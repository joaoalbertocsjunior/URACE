"""Owner-declared distribution terms; local rules, never a proof of rights or fair price."""
import math,time

DEFAULT={"schema":"urace-feature-policy-v1","access":"reviewed-direct","license_id":"LicenseRef-Owner-Reviewed-Export","essential":False,"open_after_unix":None,"resale":False}

def validate(value):
 if not isinstance(value,dict) or set(value)!=set(DEFAULT) or value.get("schema")!=DEFAULT["schema"]:raise ValueError("Unsupported feature policy")
 if value["access"] not in ("reviewed-direct","open"):raise ValueError("Unknown feature access policy")
 if not isinstance(value["license_id"],str) or not 1<=len(value["license_id"])<=160 or any(ord(c)<32 for c in value["license_id"]):raise ValueError("Explicit bounded license reference required")
 if type(value["essential"]) is not bool or type(value["resale"]) is not bool:raise ValueError("Boolean feature controls required")
 after=value["open_after_unix"]
 if after is not None and (type(after) not in (int,float) or not math.isfinite(after) or after<0):raise ValueError("Invalid explicit release time")
 if value["essential"] and value["access"]!="open":raise ValueError("Essential shared-core features cannot be exclusively paywalled")
 if value["access"]=="open" and value["license_id"].startswith("LicenseRef-Owner-Reviewed"):raise ValueError("Open sharing requires explicit reusable license terms")
 if after is not None and value["license_id"].startswith("LicenseRef-Owner-Reviewed"):raise ValueError("Timed open release requires explicit reusable license terms")
 return dict(value)

def effective(value,now=None):
 value=validate(value);now=time.time() if now is None else now
 released=value["access"]=="open" or value["open_after_unix"] is not None and now>=value["open_after_unix"]
 return {**value,"effective_access":"open" if released else "reviewed-direct","usage_price_units":0 if released else None,"rights_independently_verified":False,"ownership_transfer":False,"payment_enabled":False,"release_reason":"OWNER_PRECOMMITTED_TERMS" if released else "OWNER_REVIEW_REQUIRED","copy_prevention_guaranteed":False}
