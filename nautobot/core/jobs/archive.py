from nautobot.extras.jobs import DryRunVar, IntegerVar, Job, MultiChoiceVar

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


# TODO: This really isn't ChangeLogRotation, It's ObjectChanges + JobResult + JobConsoleEntry/JobLogEntry
#       Should either separate these into different jobs or rename this to something like `ArchiveOldRecords` (naming is hard)
class ArchiveOldRecords(Job):
    """
    Move database records that are past specific age threshold into a warm database and table.

    This job helps migrate old database records to a separate database and table in order to help optimize performance by minimizing the cardinality required for queries.
    """

    records_to_archive = MultiChoiceVar(
        choices=[(label, label) for label in ARCHIVAL_ORDER],
        description="The Database records archive. Leave empty to archive all of them.",
        required=False,
    )
    archive_age_threshold = IntegerVar(
        description=(
            "Records older than this age are selected to be archived. Leave empty to use the ARCHIVE_AGE_THRESHOLD setting."
        ),
        label="Archive Age Threshold",
        min_value=1,
        required=False,
    )
    archive_batch_size = IntegerVar(
        description=(
            "Records to move per each archival step. Leave empty to use the ARCHIVE_BATCH_SIZE setting. Lower it if the archival task runs out of memory."
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

    def run(self, *, records_to_archive=None, archive_age_threshold=None, archive_batch_size=None, dryrun=True):
        pass
