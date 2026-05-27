"""
Green Brick Road lead finder bot.
Orchestrator that ties Places + Hunter + Sheets together.

v3 changes:
- Industry filter: Places searches restricted to professional
  services types (lawyers, accountants, financial advisors,
  insurance, real estate, consultants, corporate offices,
  moving companies). Drops restaurants/retail/grocery noise.
- Founder filter: fixed substring bug where "Vice President"
  matched "president". Now uses negative patterns first to
  exclude VPs and department heads.
- Blacklist additions: J. Alexander's, Woodman's, other regional
  chains seen in real-world test run.
"""
import random
from datetime import datetime
from typing import List, Dict, Set

from src import places, apollo as hunter, sheets


# ============================================================
# CONFIG - tune these without touching the rest of the code
# ============================================================

# Hunter free tier = 25 searches/month. 5/run x 4 runs = 20/month, safe.
# UPGRADE PATH: bump to 50+ when on Hunter Starter ($34/mo).
MAX_HUNTER_CALLS_PER_RUN = 5

# Places business type filter. Only these categories are returned.
# This is the core quality lever - tightens results to professional
# services and away from consumer-facing businesses.
# To widen: add types from https://developers.google.com/maps/documentation/places/web-service/place-types
INCLUDED_BUSINESS_TYPES = [
    'lawyer',
    'accounting',
    'insurance_agency',
    'real_estate_agency',
    'consultant',
    'corporate_office',
    'moving_company',
]

# Each search returns up to 20 businesses within SEARCH_RADIUS_METERS.
SEARCH_AREAS = [
    # North shore
    (42.1711, -87.8445, "Deerfield"),
    (42.1817, -87.8003, "Highland Park"),
    (42.1275, -87.8290, "Northbrook"),
    (42.0697, -87.7878, "Glenview"),
    (42.2586, -87.8407, "Lake Forest"),
    (42.0723, -87.7228, "Wilmette"),
    (42.0451, -87.6877, "Evanston"),
    # Northwest suburbs
    (42.1664, -87.9595, "Buffalo Grove"),
    (42.0884, -87.9806, "Arlington Heights"),
    (42.1103, -88.0342, "Palatine"),
    # West suburbs
    (42.0334, -88.0834, "Schaumburg"),
    (41.7508, -88.1535, "Naperville"),
    (41.7606, -88.3201, "Aurora"),
    (41.8661, -88.1070, "Wheaton"),
    (41.8094, -88.0114, "Downers Grove"),
    (41.8850, -87.7845, "Oak Park"),
    # Chicago neighborhoods
    (41.9214, -87.6513, "Lincoln Park"),
    (41.8920, -87.6212, "River North"),
    (41.9405, -87.6533, "Lakeview"),
]
SEARCH_RADIUS_METERS = 4000

# Domains to skip - national chains, franchises, big box retail,
# regional chains seen in test runs.
DOMAIN_BLACKLIST = {
    # Fast food and restaurant chains
    'mcdonalds.com', 'subway.com', 'starbucks.com', 'dunkindonuts.com',
    'dunkin.com', 'chick-fil-a.com', 'chickfila.com', 'kfc.com',
    'pizzahut.com', 'dominos.com', 'papajohns.com', 'panera.com',
    'panerabread.com', 'applebees.com', 'olivegarden.com', 'outback.com',
    'redrobin.com', 'chilis.com', 'ihop.com', 'dennys.com',
    'dairyqueen.com', 'fiveguys.com', 'popeyes.com', 'jimmyjohns.com',
    'jerseymikes.com', 'potbelly.com', 'qdoba.com', 'moes.com',
    'pandaexpress.com', 'raisingcanes.com', 'culvers.com', 'portillos.com',
    'arbys.com', 'wingstop.com', 'buffalowildwings.com', 'hooters.com',
    'redlobster.com', 'longhornsteakhouse.com', 'texasroadhouse.com',
    'crackerbarrel.com', 'whitecastle.com', 'hardees.com', 'carlsjr.com',
    'jackinthebox.com', 'sonicdrivein.com', 'shakeshack.com',
    'sweetgreen.com', 'chipotle.com', 'tacobell.com', 'wendys.com',
    'burgerking.com', 'littlecaesars.com', 'papamurphys.com',
    'baskinrobbins.com', 'coldstonecreamery.com', 'benjerry.com',
    'timhortons.com', 'einsteinbros.com', 'noodles.com',
    'jalexanders.com',  # Regional chain seen in test
    # Big box retail and grocery
    'walmart.com', 'target.com', 'costco.com', 'samsclub.com', 'bjs.com',
    'macys.com', 'kohls.com', 'jcpenney.com', 'sears.com', 'marshalls.com',
    'tjmaxx.com', 'rossstores.com', 'gap.com', 'oldnavy.com',
    'bananarepublic.com', 'nike.com', 'adidas.com', 'lululemon.com',
    'footlocker.com', 'dickssportinggoods.com', 'bedbathandbeyond.com',
    'containerstore.com', 'michaels.com', 'hobbylobby.com',
    'dollargeneral.com', 'dollartree.com', 'familydollar.com',
    'biglots.com', 'kroger.com', 'jewel-osco.com', 'mariano.com',
    'aldi.us', 'traderjoes.com', 'wholefoodsmarket.com', 'petco.com',
    'petsmart.com', 'bestbuy.com', 'homedepot.com', 'lowes.com',
    'staples.com', 'officedepot.com', 'ulta.com', 'sephora.com',
    'bathandbodyworks.com', 'ikea.com', 'wayfair.com',
    'woodmans-food.com',  # Regional grocery chain seen in test
    # Gas and convenience
    'shell.us', 'bp.com', 'exxonmobil.com', 'chevron.com', '7-eleven.com',
    'circlek.com', 'wawa.com', 'sheetz.com', 'caseys.com',
    # Banks
    'chase.com', 'bankofamerica.com', 'wellsfargo.com', 'citi.com',
    'usbank.com', 'pnc.com', 'capitalone.com', '53.com', 'tdbank.com',
    'schwab.com', 'fidelity.com', 'vanguard.com', 'edwardjones.com',
    # Hotels
    'marriott.com', 'hilton.com', 'hyatt.com', 'ihg.com',
    'holidayinn.com', 'hamptoninn.com', 'sheraton.com', 'westin.com',
    'fourseasons.com', 'comfortinn.com', 'bestwestern.com',
    'choicehotels.com', 'wyndhamhotels.com',
    # Pharmacy
    'cvs.com', 'walgreens.com', 'riteaid.com',
    # Auto services and rentals
    'jiffylube.com', 'valvoline.com', 'midas.com', 'meineke.com',
    'goodyear.com', 'autozone.com', 'oreillyauto.com', 'pepboys.com',
    'enterprise.com', 'hertz.com', 'avis.com', 'budget.com',
    'carmax.com', 'firestonecompleteautocare.com',
    # Shipping and office services
    'fedex.com', 'ups.com', 'usps.com', 'theupsstore.com',
    # Gyms and fitness
    'planetfitness.com', 'anytimefitness.com', 'orangetheory.com',
    'lifetimefitness.com', 'lifetime.life', 'ymca.org', 'equinox.com',
    'soulcycle.com', 'purebarre.com', 'crunch.com', 'lafitness.com',
    'clubpilates.com',
    # Salons and beauty
    'greatclips.com', 'supercuts.com', 'sportclips.com',
    'haircuttery.com', 'europeanwax.com', 'massageenvy.com',
    'handandstone.com',
    # Education franchises
    'kumon.com', 'mathnasium.com', 'kindercare.com',
    'primroseschools.com', 'sylvanlearning.com',
    # Tax and services
    'hrblock.com', 'jacksonhewitt.com',
    # Tech giants
    'amazon.com', 'google.com', 'apple.com', 'microsoft.com',
}

# Seniority levels we consider founder-equivalent.
# Removed 'executive' which incorrectly matched VPs.
FOUNDER_SENIORITY = {'owner', 'partner', 'c_suite'}

# Position keywords that indicate founder-level (POSITIVE match)
FOUNDER_KEYWORDS = [
    'founder', 'co-founder', 'cofounder', 'owner',
    'ceo', 'chief executive', 'president',
    'managing director', 'managing partner',
    'proprietor',
]

# Position keywords that EXCLUDE someone even if they have a
# founder-sounding title. Checked BEFORE positive match.
# Example: "Executive Vice President" gets excluded by 'vice president'
# before it can match 'president'.
NON_FOUNDER_PATTERNS = [
    'vice president',
    'vp ', ' vp', ' vp,',
    'svp', 'evp',
    'assistant',
    'director of',
    'head of',
    'president of',  # blocks "President of Sales" etc.
    'principal engineer', 'principal scientist',
    'principal designer', 'principal architect',
    'deputy',
    'associate',
]


# ============================================================
# HELPERS
# ============================================================

def is_founder_email(email_data: Dict) -> bool:
    """
    Return True if this Hunter email looks like a founder-level contact.

    Logic:
    1. Check seniority field first (most reliable when available)
    2. If position contains any NON_FOUNDER_PATTERNS, reject
    3. If position contains any FOUNDER_KEYWORDS, accept
    """
    seniority = (email_data.get('seniority') or '').lower()
    position = (email_data.get('position') or email_data.get('title') or '').lower()

    # Strong signal: trusted seniority levels
    if seniority in FOUNDER_SENIORITY:
        return True

    # Negative filter first (catches "Vice President" before "president" matches)
    for neg in NON_FOUNDER_PATTERNS:
        if neg in position:
            return False

    # Positive filter
    if any(kw in position for kw in FOUNDER_KEYWORDS):
        return True

    return False


def label_for_biz(biz: Dict) -> str:
    """Best-effort label of where a business is located."""
    addr = biz.get('address', '')
    parts = [p.strip() for p in addr.split(',')]
    return parts[1] if len(parts) > 1 else 'Chicagoland'


# ============================================================
# PIPELINE STAGES
# ============================================================

def collect_businesses() -> List[Dict]:
    """Stage 1: search Chicagoland areas filtered by professional service types."""
    print(f"\n[Stage 1] Searching {len(SEARCH_AREAS)} areas, filtered to {len(INCLUDED_BUSINESS_TYPES)} business types...")
    all_businesses = []
    seen_place_ids = set()

    for lat, lng, label in SEARCH_AREAS:
        try:
            results = places.search_nearby(
                latitude=lat, longitude=lng,
                radius_meters=SEARCH_RADIUS_METERS,
                included_types=INCLUDED_BUSINESS_TYPES,
                max_results=20,
            )
            new_count = 0
            for biz in results:
                if biz['place_id'] in seen_place_ids:
                    continue
                seen_place_ids.add(biz['place_id'])
                all_businesses.append(biz)
                new_count += 1
            print(f"  {label}: {len(results)} found, {new_count} new")
        except Exception as e:
            print(f"  ERROR searching {label}: {e}")
            continue
    print(f"  Total unique professional service businesses: {len(all_businesses)}")
    return all_businesses


def extract_unique_domains(businesses: List[Dict]) -> List[Dict]:
    """Stage 2: convert businesses to unique domains, filter blacklist, randomize."""
    print(f"\n[Stage 2] Extracting unique domains...")
    domain_to_biz = {}
    skipped_blacklist = 0
    for biz in businesses:
        domain = places.extract_domain(biz['website'])
        if not domain:
            continue
        if domain in DOMAIN_BLACKLIST:
            skipped_blacklist += 1
            continue
        if domain not in domain_to_biz:
            domain_to_biz[domain] = biz

    domains_list = [{'domain': d, 'business': b} for d, b in domain_to_biz.items()]
    random.shuffle(domains_list)

    print(f"  Unique domains: {len(domains_list)}")
    print(f"  Skipped (blacklist): {skipped_blacklist}")
    print(f"  Order randomized for variety across runs")
    return domains_list


def find_founder_leads(
    domains_with_biz: List[Dict],
    existing_emails: Set[str],
) -> List[Dict]:
    """Stage 3: call Hunter on each new domain (capped), build lead records."""
    print(f"\n[Stage 3] Looking up founders (max {MAX_HUNTER_CALLS_PER_RUN} Hunter calls)...")
    leads = []
    calls_made = 0
    today_str = datetime.now().strftime('%Y-%m-%d')

    for entry in domains_with_biz:
        if calls_made >= MAX_HUNTER_CALLS_PER_RUN:
            print(f"  Hit Hunter call cap ({MAX_HUNTER_CALLS_PER_RUN}). Stopping.")
            break

        domain = entry['domain']
        biz = entry['business']
        calls_made += 1

        print(f"  [{calls_made}/{MAX_HUNTER_CALLS_PER_RUN}] {domain} ({biz['name']})")
        try:
            contacts = hunter.find_founders_at_domain(domain, max_results=5)
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        founders = [c for c in contacts if is_founder_email(c)]
        if not founders:
            print(f"    No founder-level contacts")
            continue

        for f in founders:
            email = (f.get('email') or '').strip().lower()
            if not email or email in existing_emails:
                continue
            name = f.get('name') or f"{f.get('first_name', '')} {f.get('last_name', '')}".strip()
            role = f.get('title') or f.get('position', '')
            lead = {
                'name': name,
                'email': email,
                'company': biz['name'],
                'domain': domain,
                'role': role,
                'location': biz.get('address', ''),
                'source': 'bot',
                'date_found': today_str,
                'status': 'new',
                'notes': f"Found via {label_for_biz(biz)} search. LinkedIn: {f.get('linkedin_url') or 'N/A'}",
                'story_score': '',
            }
            leads.append(lead)
            existing_emails.add(email)
            print(f"    + {name} ({role})")
    return leads


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Green Brick Road Lead Finder")
    print(f"  Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    businesses = collect_businesses()
    if not businesses:
        print("\nNo businesses found. Exiting.")
        return

    domains_with_biz = extract_unique_domains(businesses)
    if not domains_with_biz:
        print("\nNo qualifying domains. Exiting.")
        return

    print(f"\n[Stage 2.5] Reading existing emails from sheet for dedup...")
    existing_emails = sheets.get_existing_emails()
    print(f"  {len(existing_emails)} existing emails")

    leads = find_founder_leads(domains_with_biz, existing_emails)

    print(f"\n[Stage 4] Writing to Google Sheet...")
    if leads:
        appended = sheets.append_leads(leads)
        print(f"  Wrote {appended} new leads")
    else:
        print("  No new leads to write")

    print("\n" + "=" * 60)
    print(f"  DONE - {len(leads)} new leads found this run")
    print("=" * 60)


if __name__ == "__main__":
    main()
