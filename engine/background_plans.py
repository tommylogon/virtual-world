"""Assigned character pursuits and their short-term execution (task-426).

Compatibility facade delegating to the unified engine.plan_executor (task-702).

@module background_plans
@contributes module initialization and namespace exports
@docs docs/virtualWorld/Items & Inventory/Items Overview.md
"""
from __future__ import annotations

import logging

from engine import plan_executor

logger = logging.getLogger(__name__)

TRAVEL_MINUTES = plan_executor.TRAVEL_MINUTES
TAKE_MINUTES = plan_executor.TAKE_MINUTES
_SPATIAL = plan_executor._SPATIAL_RELATIONS

build_plan = plan_executor.build_plan
_match_item = plan_executor._match_item
_is_fixture = plan_executor._is_fixture
_carried_matching = plan_executor._carried_matching
_in_area_matching = plan_executor._in_area_matching
_check_activity_completion = plan_executor._check_activity_completion
_satisfied = plan_executor.is_step_satisfied
_run = plan_executor.execute_step
_finish = plan_executor.finish_plan
_sync_pursuit_step = plan_executor._sync_pursuit_step
maybe_assign = plan_executor.maybe_assign_pursuit
advance = plan_executor.advance_plan
