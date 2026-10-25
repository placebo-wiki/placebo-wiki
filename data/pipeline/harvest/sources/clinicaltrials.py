"""ClinicalTrials.gov registry: planned, running and finished trials, with or without posted results."""
import urllib.parse

from net import get

API = "https://clinicaltrials.gov/api/v2/studies"


def level(design: dict) -> str:
    if design.get("studyType") == "OBSERVATIONAL":
        return "observational"
    return "rct" if (design.get("designInfo") or {}).get("allocation") == "RANDOMIZED" else "trial"


CAP = 5000  # a substance has at most a few thousand registered trials, so the registry is taken in full


def fetch(substance: dict, limit: int):
    token, got = None, 0
    intr = " OR ".join(f'"{n}"' for n in substance.get("names") or [substance["en"]])
    while got < CAP:
        url = f"{API}?query.intr={urllib.parse.quote(intr)}&pageSize=1000"
        data = get(url + (f"&pageToken={token}" if token else ""))
        studies = data.get("studies", [])
        for s in studies:
            p = s["protocolSection"]
            ident, status, design = p["identificationModule"], p.get("statusModule", {}), p.get("designModule", {})
            yield {
                "source": "clinicaltrials", "source_id": ident["nctId"], "kind": "registry", "level": level(design),
                "title": ident.get("briefTitle"), "text": p.get("descriptionModule", {}).get("briefSummary"),
                "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
                "published": (status.get("startDateStruct") or {}).get("date"), "lang": "en",
                "extra": {"status": status.get("overallStatus"), "has_results": s.get("hasResults", False),
                          "phases": design.get("phases"), "masking": ((design.get("designInfo") or {}).get("maskingInfo") or {}).get("masking"),
                          "enrollment": (design.get("enrollmentInfo") or {}).get("count")},
            }
        got += len(studies)
        token = data.get("nextPageToken")
        if not studies or not token:
            return
