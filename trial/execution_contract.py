"""Version execution evidence separately from derived scoring and presentation."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROTOCOL='bounded-public-feedback-v1'

def selected_source(path,names):
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.Assign,ast.AnnAssign)) or isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    return ast.dump(ast.Module(body=nodes,type_ignores=[]),include_attributes=False)

def fingerprint(root=ROOT):
    root=Path(root)
    parts={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('executable_sandbox.py','executable_workflow.py','providers.py','stream_usage.py')}
    parts['workflow_driver']=selected_source(root/'executable_benchmark.py',{'child'})
    parts['raw_grade']=selected_source(root/'executable_scores.py',{'equal','grade'})
    parts['native_payload']=selected_source(root/'spec_trial.py',{'decode_native_payload','native'})
    parts['protocol']=PROTOCOL
    return hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest()

def analysis_fingerprint(root=ROOT):
    return hashlib.sha256((Path(root)/'executable_scores.py').read_bytes()).hexdigest()


def repository_fingerprint(root=ROOT):
    root=Path(root);core=root.parent/'runtime/urace'
    files=('project_work.py','project_tools.py','native_agents.py','repository_tasks.py','providers.py','stream_usage.py','controls.py','routing.py','resource_governor.py','common.py','source_integrity.py','trial_supervisor.py','output_quality.py','qualification_protocol.py','claude_preflight.py','decision_assessor.py','execution_contract.py','executable_sandbox.py')
    parts={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
    parts['execution_analysis']=selected_source(root/'study_analysis.py',{'category','compact_packet','context_choice','phase_telemetry'})
    parts['downstream_protocol']=selected_source(root/'downstream_study.py',{'prepare_reference','run_one','step'})
    parts['usage_ingestion']=selected_source(root/'accounting.py',{'metadata_safe','claude_usage','codex_usage','partial_lower_bound','settle'})
    parts['core_dependencies']={str(p.relative_to(core)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(core.glob('*.py'))}
    return hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest()

def measurement_fingerprint(root=ROOT):
    root=Path(root)
    names=('accounting.py','study_analysis.py','output_quality.py','coverage_assessment.py','qualification_protocol.py')
    parts={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
    return hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest()
