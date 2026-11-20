from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from pathlib import Path

from urace import command_surface, user_controls
from urace._common import (
    ROOT, CONFIG_PATH, SYSTEM_ROOT, load_config, save_config, state_path, state_lock,
)
from urace.cli_error import cli_error
from urace.cli_helpers import _help_action
from urace.inputs import queue_input
from urace.primitives import OUTPUT_SCHEMA_REGISTRY


def _cmd_executor_skills_config(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in {'executor-skills-config','context-guard-config'}:
        from urace import executor_capabilities as ec
        if _unknown:parser.error('Unknown capability configuration arguments: '+' '.join(_unknown))
        key='executor_skills' if args.command=='executor-skills-config' else 'context_guard';changes={k:getattr(args,k) for k in ('enabled','mode','max_selected','max_instruction_bytes') if getattr(args,k,None) is not None}
        try:
            if getattr(args,'catalog_file',None):
                from urace.exchange_cli import bounded_file
                changes['catalog']=json.loads(bounded_file(args.catalog_file,262144))
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config();value={**(ec.settings(config) if key=='executor_skills' else ec.context_settings(config)),**changes};ec.contract({**config,key:value})
                if changes:config[key]=value;save_config(config)
            print(json.dumps(value,indent=2,sort_keys=True));return 0
        except (ValueError,OSError,TypeError) as error:parser.error(str(error))


def _cmd_runtime_improvement_config(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='runtime-improvement-config':
        sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
        from runtime_cycle import settings as runtime_settings
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized runtime improvement arguments: '+' '.join(_unknown))
        try:
            changes={k:getattr(args,k) for k in ('enabled','auto_deploy','interval_seconds') if getattr(args,k,None) is not None}
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config();merged={**config.get('runtime_workflow',{}),**changes};updated=runtime_settings({'runtime_workflow':merged})
                if changes:config['runtime_workflow']=merged;save_config(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))


def _cmd_github_workflow_config(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='github-workflow-config':
        from urace import portfolio_github as _pgh
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized github-workflow arguments: '+' '.join(_unknown))
        try:
            _keys=('auto_pull','auto_commit','auto_push','commit_message_template','branch_strategy')
            changes={k:getattr(args,k) for k in _keys if getattr(args,k,None) is not None}
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config()
                if changes:config['github_workflow']={**_pgh.workflow_settings(config),**changes};save_config(config)
                updated=_pgh.workflow_settings(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))


def _cmd_auto_milestones_config(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='auto-milestones-config':
        from urace import milestone_suggestions as ms
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized auto-milestones arguments: '+' '.join(_unknown))
        try:
            with state_lock(CONFIG_PATH) if args.enabled is not None else nullcontext():
                config=load_config();updated=ms.settings(config)
                if args.enabled is not None:
                    updated['enabled']=args.enabled;config['auto_milestones']=updated;save_config(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))


def _cmd_decision_feedback_config(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='decision-feedback-config':
        from urace import decision_feedback as df
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized decision feedback arguments: '+' '.join(_unknown))
        try:
            config=load_config();changes={k:getattr(args,k) for k in df.DEFAULTS if getattr(args,k,None) is not None}
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config();updated=df.settings({**config,'decision_feedback':{**df.settings(config),**changes}})
                if changes:config['decision_feedback']=updated;save_config(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))


def _cmd_value_discovery_config(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in {'value-discovery-config','value-status'} or (args.command=='product' and args.action=='value'):
        from urace import value_discovery as vd
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized value command arguments: '+' '.join(_unknown))
        try:
            config=load_config()
            if args.command=='value-discovery-config':
                changes={name:getattr(args,name) for name in vd.DEFAULTS if getattr(args,name,None) is not None}
                with state_lock(CONFIG_PATH) if changes else nullcontext():
                    config=load_config();updated={**vd.settings(config),**changes};vd.settings({**config,'value_discovery':updated})
                    if changes:config['value_discovery']=updated;save_config(config)
                payload=updated
            elif args.command=='value-status':payload=vd.status(config)
            else:payload=vd.dispatch(args,config,ROOT)
            print(json.dumps(payload,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,KeyError,TypeError) as error:parser.error(str(error))


def _cmd_executor_options(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "executor-options":
        if args.model is not None and (not args.model.strip() or args.model.startswith("-") or any(ord(c) < 32 for c in args.model)):
            parser.error("model must be a nonempty model identifier")
        if args.model is not None and args.inherit_model:
            parser.error("--model and --inherit-model are mutually exclusive")
        changing = args.model is not None or args.native_effort is not None or args.inherit_model
        with state_lock(CONFIG_PATH) if changing else nullcontext():
            config = load_config()
            settings = config.setdefault("executor", {})
            known = {"codex", "claude"} | {p.get("id") for p in settings.get("providers", [])}
            if args.executor_id not in known:parser.error("unknown executor: " + args.executor_id)
            options = dict(settings.get("native_options", {}).get(args.executor_id, {}))
            if args.inherit_model:options.pop("model", None)
            elif args.model is not None:options["model"] = args.model
            if args.native_effort == "inherit":options.pop("native_effort", None)
            elif args.native_effort is not None:options["native_effort"] = args.native_effort
            if changing:
                overrides = settings.setdefault("native_options", {})
                if options:overrides[args.executor_id] = options
                else:overrides.pop(args.executor_id, None)
                save_config(config)
        print(json.dumps({"executor": args.executor_id, "native_options": options, "resource_effort": user_controls.resource_profile(config, args.executor_id)["effort"], "note": "Model/effort support is validated by the native provider at execution; settings apply to new calls."}, indent=2, sort_keys=True))
        return 0


def _cmd_auto_goals_effort(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in {"auto-goals", "effort"}:
        if args.command == "auto-goals" and args.value is not None and args.action != "replenish":parser.error("enable/disable takes no extra value; use auto-goals replenish enable|disable")
        if args.command == "effort" and args.mode == "inherit" and not args.executor_id:parser.error("inherit requires --executor")
        changing = (args.action not in {"status"} and (args.action != "replenish" or args.value not in {None,"status"})) if args.command == "auto-goals" else args.mode != "status"
        with state_lock(CONFIG_PATH) if changing else nullcontext():
            config = load_config()
            if args.command == "auto-goals":
                action = args.value or "status" if args.action == "replenish" else args.action
                if action != "status":config.setdefault("auto_goals", {})["replenish_backlog" if args.action == "replenish" else "enabled"] = action == "enable";save_config(config)
                payload = user_controls.auto_goals(config)
            else:
                settings = config.setdefault("resources", {})
                known = {"codex", "claude"} | {p.get("id") for p in config.get("executor", {}).get("providers", [])}
                if args.executor_id and args.executor_id not in known:parser.error("unknown executor: " + args.executor_id)
                if args.mode != "status":
                    if args.executor_id:
                        overrides = settings.setdefault("executor_effort", {})
                        if args.mode == "inherit":overrides.pop(args.executor_id, None)
                        else:overrides[args.executor_id] = args.mode
                    else:settings["effort"] = args.mode
                    save_config(config)
                payload = {"global": settings.get("effort", "medium"), "per_executor": settings.get("executor_effort", {}), "effective": {p:user_controls.effort_mode(settings,p) for p in sorted(known) if p is not None}}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0


def _cmd_configuration_self_evolution(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in {"configuration", "self-evolution"}:
        config = load_config()
        setting = "self-evolution" if args.command == "self-evolution" else args.setting
        value = args.mode if args.command == "self-evolution" else args.value
        if setting == "show" or (value in {None,"status"} and (setting!="executor-budget" or (args.daily is None and args.monthly is None))):
            self_mode = {"NECESSARY_ONLY": "auto", "CONTINUOUS": "always", "DISABLED": "never"}.get(str(config.get("self_evolution_policy", {}).get("mode", "NECESSARY_ONLY")).upper(), "auto")
            payload = {"self-evolution": self_mode, "change-explanations": config.get("change_explanations", {}).get("mode", "disabled"), "external-metrics": config.get("external_metrics", {}).get("mode", "DISABLED").lower().replace("_", "-"), "analytics-export": config.get("analytics_export", {}).get("mode", "DISABLED").lower().replace("_", "-"), "executor-budget": {"daily": config.get("executor", {}).get("max_executor_calls_per_24h"), "monthly": config.get("executor", {}).get("max_executor_calls_per_30d")}, "evaluation": config.get("evaluation_system", {})}
            payload["workflow"] = config.get("execution_workflow", "core")
            from urace.value_discovery import settings as value_settings
            payload["value-discovery"] = value_settings(config)
            payload.update({"auto-goals":user_controls.auto_goals(config),"effort":{"global":config.get("resources",{}).get("effort","medium"),"per_executor":config.get("resources",{}).get("executor_effort",{})},"native-executors":config.get("executor",{}).get("native_options",{})})
            print(json.dumps(payload, indent=2, sort_keys=True) if args.json else "\n".join(f"{key}: {value}" for key, value in payload.items()))
            return 0
        if setting == "workflow":
            if value not in {"core", "specification-trial"}: parser.error("workflow must be core or specification-trial")
            with state_lock(state_path(config)):
                config["execution_workflow"] = value
                save_config(config)
            print(json.dumps({"status":"configured","workflow":value,"applies":"new auto invocations"}))
            return 0
        if setting == "self-evolution":
            aliases = {"auto": "NECESSARY_ONLY", "always": "CONTINUOUS", "never": "DISABLED"}
            if value not in aliases: parser.error("self-evolution must be auto, always, or never")
            queued = queue_input(config, "policy_control", {"name": "self-evolution", "value": aliases[value]})
        elif setting == "change-explanations":
            if value not in {"auto", "enabled", "disabled"}: parser.error("change-explanations must be auto, enabled, or disabled")
            queued = queue_input(config, "policy_control", {"name": "change-explanations", "value": value})
        elif setting == "external-metrics":
            aliases = {"disabled": "DISABLED", "provided-only": "PROVIDED_ONLY", "discover-public-and-use-provided": "DISCOVER_PUBLIC_AND_USE_PROVIDED"}
            if value not in aliases: parser.error("external-metrics must be disabled, provided-only, or discover-public-and-use-provided")
            queued = queue_input(config, "policy_control", {"name": "external-metrics", "value": aliases[value]})
        elif setting == "analytics-export":
            aliases = {"disabled": "DISABLED", "on-demand": "ON_DEMAND", "on-checkpoint": "ON_CHECKPOINT"}
            if value not in aliases: parser.error("analytics-export must be disabled, on-demand, or on-checkpoint")
            queued = queue_input(config, "policy_control", {"name": "analytics-export", "value": aliases[value]})
        elif setting == "executor-budget":
            if value=="unlimited" and args.daily is None and args.monthly is None:daily=monthly=None
            else:
                daily=args.daily if args.daily is not None else config.get("executor",{}).get("max_executor_calls_per_24h")
                monthly=args.monthly if args.monthly is not None else config.get("executor",{}).get("max_executor_calls_per_30d")
                command_surface.validate_budget(daily,monthly,parser)
            queued = queue_input(config,"budget_control",{"daily":daily,"monthly":monthly})
        else:
            try: numeric = float(value) if value is not None else None
            except ValueError: parser.error(f"{setting} requires a numeric value")
            if numeric is None: parser.error(f"{setting} requires a numeric value")
            action = "set-minimum" if setting == "evaluation-minimum" else "set-weight"
            if action == "set-weight" and not args.component: parser.error("evaluation-weight requires --component")
            numeric=command_surface.validate_evaluation(config,action,args.component,numeric,parser)
            queued = queue_input(config, "evaluation_control", {"action": action, "component": args.component, "value": numeric})
        print(json.dumps({"status":"queued","setting":setting,"value":value,"id":queued["id"],"applies":"next safe boundary"}) if args.json else f"Queued {setting}={value}; it will apply at the next safe boundary")
        return 0


def _cmd_schema(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "schema":
        if args.action == "help":
            return _help_action("""URACE Schema Guide
    ═══════════════════
    Inspect the output schema registry (OutputSchemaRegistry §62l).

      urace schema list                         -- list all registered --json output schemas
      urace schema inspect <command>            -- inspect the schema for a specific command
      urace schema export                       -- export all schema registries
      urace schema export --target output-schemas  -- export only output schemas
      urace schema export --target bundles      -- export only feature bundles

    Example:
      urace schema inspect "check"     -- show the stable fields for urace check --json""", args)
        if args.action == "list":
            schemas = [{"command": cmd, "schema_version": info["version"], "stable_since": info["stable_since"]}
                       for cmd, info in sorted(OUTPUT_SCHEMA_REGISTRY.items())]
            if args.json:
                print(json.dumps({"schema_version": "1.0", "schemas": schemas}, indent=2, sort_keys=True))
            else:
                for s in schemas:
                    print(f"{s['command']:25s}  v{s['schema_version']}  (since {s['stable_since']})")
            return 0

        elif args.action == "inspect":
            cmd_name = " ".join(args.schema_command)
            info = OUTPUT_SCHEMA_REGISTRY.get(cmd_name)
            if not info:
                print(f"No registered schema for command: {cmd_name}", file=sys.stderr)
                return 1
            payload = {"schema_version": "1.0", "command": cmd_name,
                       "output_schema_version": info["version"],
                       "stable_since": info["stable_since"],
                       "fields": info["fields"]}
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(f"Command:        {cmd_name}")
                print(f"Schema version: {info['version']}")
                print(f"Stable since:   {info['stable_since']}")
                print(f"Fields:         {', '.join(info['fields'])}")
            return 0

        elif args.action == "export":
            from urace import schema_export as _sch_exp
            target = getattr(args, "target", "all")
            if target == "output-schemas":
                payload = _sch_exp.export_output_schemas()
            elif target == "bundles":
                payload = _sch_exp.export_feature_bundles()
            else:
                payload = _sch_exp.export_all()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                if target in ("output-schemas", "all"):
                    schemas = payload.get("output_schemas", payload.get("schemas", []))
                    print(f"Output schemas ({len(schemas)}):")
                    for s in schemas:
                        print(f"  {s['command']:25s}  v{s['schema_version']}  (since {s['stable_since']})")
                if target in ("bundles", "all"):
                    bundles = payload.get("feature_bundles", payload.get("bundles", []))
                    print(f"Feature bundles ({len(bundles)}):")
                    for b in bundles:
                        print(f"  {b['name']:30s}  {b['spec_version']:6s}  [{b['source']}]")
            return 0
