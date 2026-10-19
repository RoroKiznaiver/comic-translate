"""Which step of the simple flow (Import, Translate, Export) is the user on?

Kept free of any Qt import so it can be unit-tested anywhere.
"""

STEP_IMPORT = 0
STEP_TRANSLATE = 1
STEP_EXPORT = 2
STEP_COUNT = 3


def compute_step_index(has_pages: bool, running: bool, finished: bool) -> int:
    """Map the workspace state to a step.

    has_pages: at least one page is loaded (the drop zone is not showing)
    running:   a batch translation is in progress
    finished:  a batch has completed (and was not cancelled) since the last import
    """
    if running:
        return STEP_TRANSLATE
    if not has_pages:
        return STEP_IMPORT
    if finished:
        return STEP_EXPORT
    return STEP_TRANSLATE
