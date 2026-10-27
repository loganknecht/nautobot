from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
from django.utils import timezone

from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.jobs import DryRunVar, IntegerVar, Job, MultiChoiceVar
from nautobot.extras.models import ArchivedObjectChange, ObjectChange
from nautobot.extras.signals import _handle_deleted_object

name = "System Jobs"

# Archival order matters, used to determine what gets archived first to remove issues with cascading deletions
ARCHIVAL_ORDER = (
    "extras.objectchange",  # Independent
    # --------------------
    "extras.jobresult",  # Parent to JobConsoleEntry, Parent to JobLogEntry
    "extras.joblogentry",  # Dependent on JobResult
    "extras.jobconsoleentry",  # Dependent on JobResult
)
# TODO: Ask about FileProxy which is dependent on JobResult

# The records that can be archived are displayed in alphabetical order
# But `ARCHIVAL_ORDER` is the actual order that archival occurs in
ARCHIVAL_DISPLAY_ORDER = tuple(sorted(ARCHIVAL_ORDER))


# TODO: This really isn't ChangeLogRotation, It's ObjectChanges + JobResult + JobConsoleEntry/JobLogEntry
#       Should either separate these into different jobs or rename this to something like `ArchiveOldRecords` (naming is hard)
class ArchiveOldRecords(Job):
    """
    Move database records that are past specific age threshold into a warm database and table.

    This job helps migrate old database records to a separate database and table in order to help optimize performance by minimizing the cardinality required for queries.
    """

    ui_selected_models_to_archive = MultiChoiceVar(
        choices=[(label, label) for label in ARCHIVAL_DISPLAY_ORDER],
        description="The Database records archive. Leave empty to archive all of them.",
        label="Models To Archive",
        required=False,
    )
    ui_archive_age_threshold = IntegerVar(
        description=(
            "Records older than this age are selected to be archived. Leave empty to use the ARCHIVE_MODEL_DEFAULT_AGE_THRESHOLD setting."
        ),
        label="Archive Age Threshold",
        min_value=1,
        required=False,
    )
    ui_archive_batch_size = IntegerVar(
        description=(
            "Records to move per each archival step. Leave empty to use the ARCHIVE_MODEL_DEFAULT_BATCH_SIZE setting. Lower it if the archival task runs out of memory."
        ),
        label="Archive Batch Size",
        min_value=1,
        required=False,
    )
    dryrun = DryRunVar(description="Report what would be archived without moving anything.")

    class Meta:
        name = "Archive Old Records"
        description = "This job will migrate the specified Model records to a separate databse and table in order to reduce cardinality of the existing database."
        has_sensitive_variables = False
        dryrun_default = True

    def run(
        self,
        *,
        ui_selected_models_to_archive=None,
        ui_archive_age_threshold=None,
        ui_archive_batch_size=None,
        dryrun=True,
    ):
        selected_models = set(ui_selected_models_to_archive or ARCHIVAL_ORDER)
        dependency_sorted_models_to_archive = [
            model_label for model_label in ARCHIVAL_ORDER if model_label in selected_models
        ]

        archive_model_age_threshold = ui_archive_age_threshold or get_settings_or_config(
            "ARCHIVE_MODEL_DEFAULT_AGE_THRESHOLD"
        )
        archive_model_batch_size = ui_archive_batch_size or get_settings_or_config("ARCHIVE_MODEL_DEFAULT_BATCH_SIZE")

        for model_label in dependency_sorted_models_to_archive:
            if model_label == "extras.objectchange":
                self._archive_object_changes(archive_model_age_threshold, archive_model_batch_size, dryrun)
            # TODO: extras.jobresult, which carries its log and console entries with it.

    def _archive_object_changes(self, age_threshold, batch_size, dryrun):
        pass
        # TODO

    def _archive_object_change_batch(self, batch):
        pass
        # TODO
