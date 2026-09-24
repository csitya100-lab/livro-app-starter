import requests, time, xml.etree.ElementTree as ET, json, sys
BASE="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
def esearch(term, n=5):
    for att in range(4):
        r=requests.get(BASE+"esearch.fcgi",params={"db":"pubmed","term":term,"retmax":n,"retmode":"json"},timeout=30)
        time.sleep(0.5)
        try: return r.json()["esearchresult"].get("idlist",[])
        except Exception: time.sleep(2)
    return []
def efetch(pmids):
    if not pmids: return {}
    root=None
    for att in range(4):
        r=requests.get(BASE+"efetch.fcgi",params={"db":"pubmed","id":",".join(pmids),"retmode":"xml"},timeout=60)
        time.sleep(0.5)
        try: root=ET.fromstring(r.content); break
        except Exception: time.sleep(2)
    out={}
    if root is None: return out
    for art in root.findall(".//PubmedArticle"):
        pmid=art.findtext(".//PMID")
        a=art.find(".//Article")
        tnode=a.find("ArticleTitle")
        title="".join(tnode.itertext()).strip() if tnode is not None else ""  # itertext: títulos com <i>gene</i> não são truncados
        j=a.find("Journal")
        jab=j.findtext("ISOAbbreviation") or j.findtext("Title") or ""
        vol=j.findtext("JournalIssue/Volume") or ""; iss=j.findtext("JournalIssue/Issue") or ""
        year=j.findtext("JournalIssue/PubDate/Year") or (j.findtext("JournalIssue/PubDate/MedlineDate") or "")[:4]
        pages=a.findtext("Pagination/MedlinePgn") or ""
        eloc=[e.text for e in a.findall("ELocationID") if e.get("EIdType")=="pii"]
        doi=[e.text for e in a.findall("ELocationID") if e.get("EIdType")=="doi"]
        if not doi:
            doi=[i.text for i in art.findall(".//ArticleId") if i.get("IdType")=="doi"]
        auths=[]
        for au in a.findall("AuthorList/Author"):
            ln=au.findtext("LastName"); ini=au.findtext("Initials"); coll=au.findtext("CollectiveName")
            if ln: auths.append(f"{ln} {ini or ''}".strip())
            elif coll: auths.append(coll)
        out[pmid]=dict(pmid=pmid,title=title,journal=jab,year=year,vol=vol,iss=iss,pages=pages or (eloc[0] if eloc else ""),doi=doi[0] if doi else "",authors=auths)
    return out
def vancouver(m):
    au=m["authors"]
    s=", ".join(au[:6])+(", et al" if len(au)>6 else "")
    t=m["title"].rstrip(".")
    v=f"{m['year']};{m['vol']}" + (f"({m['iss']})" if m['iss'] else "") + (f":{m['pages']}" if m['pages'] else "")
    return f"{s}. {t}. {m['journal']}. {v}." + (f" doi:{m['doi']}" if m['doi'] else "") + f" PMID: {m['pmid']}."
