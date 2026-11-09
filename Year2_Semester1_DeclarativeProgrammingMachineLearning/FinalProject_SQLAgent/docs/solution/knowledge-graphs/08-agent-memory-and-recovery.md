# Knowledge Graph 08 — Agent Memory Schema and Crash Recovery

## 1. Persistent Memory Entity-Relationship Diagram (`data/agent_memory.db`)

```mermaid
erDiagram
    task_runs ||--o| task_plans : "has_plan (CASCADE)"
    task_runs ||--o{ task_steps : "executes_steps (CASCADE)"
    task_runs ||--o{ task_decisions : "records_decisions (CASCADE)"
    task_runs ||--o{ task_tool_calls : "audits_calls (CASCADE)"
    task_runs ||--o{ task_artifacts : "produces_artifacts (CASCADE)"
    task_runs ||--o{ task_checkpoints : "snapshots (CASCADE)"
    task_runs ||--o{ recovery_attempts : "recovers (CASCADE)"
    task_runs ||--o{ interrupted_operations : "tracks_idempotency (CASCADE)"
    task_checkpoints ||--o{ recovery_attempts : "restored_from (SET NULL)"

    task_runs {
        TEXT task_id PK
        TEXT user_request
        TEXT status
        TEXT current_step
        TEXT created_at
        TEXT updated_at
        TEXT error
        JSON metadata
    }
    task_plans {
        TEXT plan_id PK
        TEXT task_id FK
        TEXT rationale
        TEXT created_at
    }
    task_steps {
        TEXT step_id PK
        TEXT task_id FK
        INTEGER step_order
        TEXT name
        TEXT description
        TEXT required_skill
        JSON required_tools
        JSON dependencies
        JSON optional_dependencies
        TEXT status
        TEXT output_reference
        TEXT error
        JSON metadata
    }
    task_checkpoints {
        TEXT checkpoint_id PK
        TEXT task_id FK
        INTEGER sequence_number
        TEXT checkpoint_type
        INTEGER schema_version
        TEXT task_status
        TEXT current_stage
        TEXT current_step_id
        TEXT completed_step_ids
        TEXT pending_step_ids
        TEXT failed_step_ids
        TEXT step_states
        TEXT decision_ids
        TEXT pending_approval
        TEXT artifact_ids
        TEXT checksum
        TEXT created_at
    }
    recovery_attempts {
        TEXT attempt_id PK
        TEXT task_id FK
        TEXT checkpoint_id FK
        TEXT policy
        TEXT status
        TEXT failure_reason
        TEXT details
        TEXT created_at
        TEXT completed_at
    }
    interrupted_operations {
        TEXT operation_id PK
        TEXT task_id FK
        TEXT step_id
        TEXT operation_type
        TEXT operation_key
        TEXT status
        TEXT error
        TEXT payload
        TEXT result_summary
    }
    semantic_facts {
        TEXT fact_id PK
        TEXT category
        TEXT subject
        TEXT fact
        TEXT provenance
        INTEGER is_validated
    }
    skill_registry {
        TEXT skill_id PK
        TEXT name
        TEXT domain
        TEXT version
        TEXT file_path
        INTEGER is_enabled
        TEXT last_discovered_at
    }
```

The entity-relationship diagram above shows the relational schema of `data/agent_memory.db` across migrations `001`, `002`, and `003`.

---

## 2. Deterministic Task Recovery Flow (Scenarios A through F)

```mermaid
flowchart TD
    Start["CheckpointManager.recover_task(task_id, policy)"]
    CheckTerm{"task.status ==<br/>COMPLETED?"}
    ReturnComp["Return SUCCESS<br/>(Terminal state protected)"]
    CheckPol{"policy ==<br/>MANUAL_ONLY?"}
    PauseMan["Transition to REQUIRES_RECOVERY<br/>Return REQUIRES_CONFIRMATION"]

    CheckScenA{"Scenario A:<br/>PENDING & no steps?"}
    RetA["Return SUCCESS<br/>(Ready for fresh start)"]

    FindChk["Scan get_checkpoint_history(task_id) in reverse<br/>Validate SHA-256 checksum, schema_version, DAG & artifacts"]
    CheckScenB{"Scenario B:<br/>status == PLANNING &<br/>no checkpoint?"}
    RetB["Reuse persisted plan or reset to PENDING<br/>Return SUCCESS"]

    HasChk{"Valid checkpoint<br/>found?"}
    FailNoChk["Transition to REQUIRES_RECOVERY<br/>Return FAILED"]

    Restore["restore_checkpoint(valid_checkpoint.checkpoint_id)"]
    CheckScenF{"Scenario F:<br/>WAITING_FOR_APPROVAL<br/>or pending_approval?"}
    RetF["Maintain WAITING_FOR_APPROVAL<br/>Return REQUIRES_CONFIRMATION (requires_user_action=True)"]

    ReconcileOps["Scenarios D & E: Reconcile interrupted_operations<br/>• Scenario D (SQL): Mark interrupted, safe to re-run read-only<br/>• Scenario E (Report): Reuse valid on-disk PDF/CSV or schedule regeneration"]
    NextStep["Scenario C: Advance Execution Pointer<br/>Reset in-flight RUNNING step -> READY<br/>Promote dependency-satisfied PENDING step -> READY"]
    SaveRec["Create RECOVERY_COMPLETED checkpoint<br/>Return RecoveryResult(success=True)"]

    Start --> CheckTerm
    CheckTerm -->|"Yes"| ReturnComp
    CheckTerm -->|"No"| CheckPol
    CheckPol -->|"Yes"| PauseMan
    CheckPol -->|"No"| CheckScenA
    CheckScenA -->|"Yes"| RetA
    CheckScenA -->|"No"| FindChk --> CheckScenB
    CheckScenB -->|"Yes"| RetB
    CheckScenB -->|"No"| HasChk
    HasChk -->|"No"| FailNoChk
    HasChk -->|"Yes"| Restore --> CheckScenF
    CheckScenF -->|"Yes"| RetF
    CheckScenF -->|"No"| ReconcileOps --> NextStep --> SaveRec
```

The recovery decision flowchart above traces how `CheckpointManager.recover_task()` (`agent/checkpoint_manager.py`) handles Scenarios A through F while verifying SHA-256 checkpoint integrity and protecting human approval gates.
