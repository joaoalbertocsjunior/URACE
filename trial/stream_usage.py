"""Retain usage from completed native stream messages without storing reasoning."""
import hashlib,json
def structured_diagnostics(event):
    """Retain bounded failure provenance without retaining error/prompt text."""
    errors=event.get('errors')
    if not isinstance(errors,list):
        return {'available':False,'reason':'Provider did not return an errors array','count':None,'categories':[]}
    categories=set()
    for item in errors[:16]:
        text=str(item).lower()[:8192]
        for marker in ('schema','validation','fallback','retract','max_tokens','timeout','quota','rate_limit'):
            if marker in text:categories.add(marker)
    try:signature=hashlib.sha256(json.dumps(errors,sort_keys=True,allow_nan=False).encode()).hexdigest()
    except (ValueError,TypeError,RecursionError):signature=None
    return {'available':True,'count':len(errors),'classified_errors':min(16,len(errors)),
            'categories':sorted(categories),'sha256':signature,
            'raw_error_text_retained':False}

class StreamUsage:
    def __init__(self):self.messages={};self.final=None
    def ingest(self,event):
        if event.get('type')=='assistant':
            message=event.get('message',{});identity=message.get('id');usage=message.get('usage')
            if identity and isinstance(usage,dict):
                prior=self.messages.get(identity,{})
                if prior and prior['model']!=message.get('model'):raise ValueError('Message ID reused across models')
                fields=('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')
                values={key:max((prior.get('usage') or {}).get(key,0),usage.get(key,0)) for key in fields}
                self.messages[identity]={'model':message.get('model'),'usage':values}
        if event.get('type')=='result':
            self.final={key:event.get(key) for key in ('is_error','subtype','duration_ms','duration_api_ms','total_cost_usd','usage','modelUsage','structured_output','result')}
            self.final['structured_output_diagnostics']=structured_diagnostics(event)
    def snapshot(self):
        return {'completed_message_usage':dict(self.messages),'final':self.final,'all_auxiliary_usage_known':self.final is not None and self.final.get('modelUsage') is not None,'subscription_credit_decrement':None,'success':self.final is not None and self.final.get('is_error') is False}

def claude_transport_policy():
    return {'version':3,'structured_output_retries':3,'max_turns':4,'output_token_limit':8192}

def next_claude_controls():
    policy=claude_transport_policy()
    return {'CLAUDE_CODE_MAX_RETRIES':'0','MAX_STRUCTURED_OUTPUT_RETRIES':str(policy['structured_output_retries']),'CLAUDE_CODE_MAX_OUTPUT_TOKENS':str(policy['output_token_limit'])}
