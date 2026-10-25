"""Collectors, one per site. Each exposes fetch(substance, limit) yielding findings for base.add."""
from . import clinicaltrials, cyberleninka, europepmc, openfda, reddit, stubs

ALL = {
    "europepmc": europepmc.fetch,
    "clinicaltrials": clinicaltrials.fetch,
    "openfda": openfda.fetch,
    "cyberleninka": cyberleninka.fetch,
    "reddit": reddit.fetch,
    **stubs.ALL,
}
