import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth_service import (
    register_user,
    login_user,
    get_current_user,
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    update_user_profile,
)
from services.exercise_service import (
    search_exercises,
    get_exercise_by_id,
    get_exercise_detail,
    add_exercise,
    edit_exercise,
    delete_exercise,
    get_exercise_history_for_user,
    get_exercise_prs,
    get_all_muscle_groups,
    get_all_equipment_types,
    get_all_exercises,
    get_exercise_count,
    check_exercise_name_exists,
)
from services.workout_service import (
    log_workout,
    get_workout_history,
    get_workout_detail,
    edit_workout,
    delete_workout,
    get_weekly_activity,
    get_workout_stats,
    get_recent_workouts,
    get_workouts_for_calendar,
    get_workouts_with_stats,
    get_total_workouts,
    get_total_exercises_logged,
    get_pr_set_ids_for_workout,
)
from services.template_service import (
    create_template,
    clone_template,
    edit_template,
    delete_template,
    get_user_templates,
    get_system_templates,
    get_template_detail,
    get_all_templates_for_user,
    create_template_from_workout_exercises,
    enrich_template_exercises,
)
from services.measurement_service import (
    log_measurement,
    get_measurement_history,
    get_measurement_by_id,
    edit_measurement,
    delete_measurement,
    get_trend_summary,
    get_current_weight,
    get_all_measurements_for_user,
)
from services.progress_service import (
    get_streak_stats,
    get_muscle_group_distribution,
    get_personal_records_summary,
    get_recent_prs,
    get_workout_consistency,
    get_weekly_activity as progress_get_weekly_activity,
    get_workouts_this_week,
    get_total_workouts as progress_get_total_workouts,
)
from services.pr_service import (
    detect_prs,
    get_personal_records,
    get_recent_prs as pr_get_recent_prs,
    get_pr_set_ids_for_workout as pr_get_pr_set_ids_for_workout,
    get_exercise_prs as pr_get_exercise_prs,
)