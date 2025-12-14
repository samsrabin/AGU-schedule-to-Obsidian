import regex as re
import time
from os import path, rename, remove, chdir, makedirs
from datetime import datetime
from zipfile import ZipFile
import sys
from configparser import ConfigParser

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

delay = 60  # timeout, seconds

browser = None
INDENT = 4 * " "


def truncate_filename(filename):
    filepath = path.split(filename)
    pardir = path.join(*filepath[:-1])
    orig_basename = path.basename(filename)
    basename = orig_basename
    max_basename_length = 255
    Ndrop = 0
    while len(basename) > max_basename_length:
        # Remove the last word of the filename (replace with ellipsis) and try again
        Ndrop += 1
        prev_basename = basename
        name, ext = path.splitext(orig_basename)
        name_list = name.split(" ")
        basename = " ".join(name_list[:-Ndrop]) + " …" + ext
        if basename == prev_basename:
            raise RuntimeError("Infinite loop in truncate_filename()")
    return path.join(pardir, basename)


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.dirname(__file__)
    return path.join(base_path, relative_path)


# Set defaults
thisYear = datetime.now().year
debug = False
overwrite = False

# Read settings file
settings_file = "settings.ini"
if path.exists(settings_file):
    config = ConfigParser()
    config.read(settings_file)
    if config.has_option("optional", "year"):
        thisYear = config.get("optional", "year")
        thisYear = int(thisYear)
    if config.has_option("optional", "output_location"):
        outDir = config.get("optional", "output_location")
        if not path.exists(outDir):
            makedirs(outDir)
        chdir(outDir)
    if config.has_option("optional", "debug"):
        debug = config.get("optional", "debug").lower() == "true"
    if config.has_option("optional", "overwrite"):
        overwrite = config.get("optional", "overwrite").lower() == "true"


def start_browser():
    # Selenium will download the necessary version of Chrome For Testing
    service = Service()
    options = webdriver.ChromeOptions()
    if not debug:
        options.add_argument("--headless")  # Invisible window
    browser = webdriver.Chrome(service=service, options=options)

    if thisYear in [2022]:
        tz = "America/Chicago"
    elif thisYear in [2023]:
        tz = "US/Pacific"
    elif thisYear in [2024]:
        tz = "US/Eastern"
    elif thisYear in [2025]:
        tz = "US/Central"
    else:
        raise KeyError(f"What time zone for AGU {thisYear}?")

    tz_params = {"timezoneId": tz}
    browser.execute_cdp_cmd("Emulation.setTimezoneOverride", tz_params)
    return browser


# Parse "summary" into event title and code (if any)
def summary_to_codetitle(summary, parent_code=None):
    # Remove extraneous information
    summary = summary.replace("NCA5 Author\n", "")
    if parent_code:
        code = re.findall(parent_code + r"\-\d+ ", summary)
    else:
        code = re.findall(r"[\d\-A-Z]+ - ", summary)
    if not code:
        code = re.findall(r"^[\d\-A-Z]+ ", summary)
    if code:
        title = summary.replace(code[0], "")
        code = code[0].replace(" - ", "")
        code = code.replace(" ", "")
    else:
        title = summary
    return code, title


# Replace illegal characters for Obsidian filenames
def codetitle_to_filename(code, title):
    if code:
        filename = f"{code} {title}"
    else:
        filename = title
    if ":" in filename:
        filename = filename.replace(": ", "—")
        filename = filename.replace(":", "—")
    if "?" in filename:
        filename = filename.replace("?", "")
    if "/" in filename:
        filename = filename.replace("/", "-")
    for c in ["*", '"', "\\", "/", "<", ">", ":", "|", "?"]:
        if c in filename:
            raise RuntimeError(f"Illegal character {c} in filename: '{filename}'")
    return filename


def do_replace(output_file):
    old_file = output_file.replace(
        ".md", " " + datetime.now().strftime("%Y%m%d%H%M%S") + ".md"
    )
    file_archive = output_file.replace(".md", " ARCHIVE.zip")
    rename(output_file, old_file)
    with ZipFile(file_archive, "a") as zipObj:
        zipObj.write(old_file)
    remove(old_file)


def find_or_none(driver, classname):
    x = driver.find_elements(By.CLASS_NAME, classname)
    if len(x) > 0:
        x = x[0].text
    else:
        x = None
    return x


def get_presentation(
    url,
    session_urls,
    browser=None,
    title=None,
    has_abstract=True,
    author_list2=None,
):
    if not browser:
        browser = start_browser()

    printed_title = False
    if title:
        print(f"Importing presentation: {title}")
        printed_title = True

    if debug:
        print("URL: " + url)
    browser.get(url)
    start_time = datetime.now()
    abstract_failed = False
    try:
        WebDriverWait(browser, delay).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "field_ParentList_ParentEntries")
            )
        )
        remaining_time = max(1, delay - (datetime.now() - start_time).total_seconds())
        if has_abstract:
            try:
                WebDriverWait(browser, remaining_time).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "field_Abstract"))
                )
            except TimeoutException:
                has_abstract = False
                abstract_failed = True
            remaining_time = max(
                1, delay - (datetime.now() - start_time).total_seconds()
            )
        if not author_list2:
            try:
                WebDriverWait(browser, remaining_time).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "RoleListItem"))
                )
            except TimeoutException:
                pass
    except TimeoutException:
        print(f"    Loading took too much time (limit {delay} seconds). Url: {url}")
        has_abstract = False

    # Parent session
    parent = browser.find_element(By.CLASS_NAME, "field_ParentList_ParentEntries")
    tries = 0
    parent2 = None
    while not parent2 and tries < 15:
        tries = tries + 1
        try:
            parent2 = parent.find_element(By.TAG_NAME, "a")
        except:
            time.sleep(1)
    if not parent2:
        raise RuntimeError("Parent session info not found!")
    parent_session_code, parent_session_title = summary_to_codetitle(parent2.text)
    parent_session_filename = "_" + codetitle_to_filename(
        parent_session_code, parent_session_title
    )
    parent_session_url = parent2.get_property("href")
    if parent_session_url not in session_urls:
        session_urls = session_urls + [parent_session_url]
    if debug:
        print(f"Parent session: {parent_session_title} ({parent_session_url})")
        print(f"Parent session filename: {parent_session_filename}")

    # Parse "summary" into event title and code (if any)
    code, title = summary_to_codetitle(
        browser.find_element(By.CLASS_NAME, "titleContent").text,
        parent_session_code,
    )
    if not code:
        code = f"{parent_session_code}-XX"
    if not printed_title:
        print(f"Importing presentation: {title}")
    if abstract_failed:
        print("    (No abstract found)")
    if debug:
        print(f"Code: {code}")
        print(f"Title: {title}")

    # Replace illegal characters for Obsidian filenames
    filename = codetitle_to_filename(code, title)
    filename_md = filename + ".md"
    filename_md = truncate_filename(filename_md)
    output_file = filename_md
    if debug:
        print(f"Output file: '{output_file}'")

    if path.isfile(output_file):
        if not overwrite:
            print("Won't overwrite existing paper file: " + output_file)
            return session_urls
        do_replace(output_file)
    if debug:
        print(f"Filename: '{filename}'")
        print(f"Filename (md): '{filename_md}'")

    # Abstract
    if has_abstract:
        if debug:
            print("Getting abstract")
        abstract = browser.find_element(By.CLASS_NAME, "field_Abstract").text.replace(
            "Abstract\n", ""
        )
        abstract = abstract.replace("\n", "\n\n")
        abstract = abstract.replace("\n\n\n", "\n\n")
        if debug:
            print(f"Abstract: {abstract}")
    else:
        abstract = ""

    # P-L Summary
    pl_summary = None
    field_ExtendedAbstract = browser.find_elements(
        By.CLASS_NAME, "field_ExtendedAbstract"
    )
    if len(field_ExtendedAbstract) > 0:
        pl_summary = field_ExtendedAbstract[0].text.replace(
            "Plain-language Summary\n", ""
        )
        pl_summary = pl_summary.replace("\n", "\n\n")
        pl_summary = pl_summary.replace("\n\n\n", "\n\n")
    if debug:
        print(f"Plain-language summary: {pl_summary}")

    # Authors
    if not author_list2:
        authors = browser.find_elements(By.CLASS_NAME, "RoleListItem")
        author_list = ""
        author_names = []
        author_insts = []
        author_insts_all = []
        for a, author in enumerate(authors):
            name = None
            tries = 0
            while not name and tries < 15:
                tries = tries + 1
                try:
                    author_split = author.text.split("\n")
                    name = author_split[1]
                    if len(author_split) > 2:
                        institution = author_split[2]
                    else:
                        institution = None
                except:
                    time.sleep(1)
            if not name:
                raise RuntimeError("Author info not found!")
            author_list = author_list + f"{name} ({institution})"
            if a < len(authors) - 1:
                author_list = author_list + ", "
            author_names = author_names + [name]
            author_insts_all = author_insts_all + [institution]
            if institution:
                if institution not in author_insts:
                    author_insts = author_insts + [institution]
        ## print(author_list)
        author_list2 = ""
        for a, author in enumerate(author_names):
            inst = author_insts_all[a]
            if inst:
                inst_num = author_insts.index(inst) + 1
                author_list2 = author_list2 + f"{author} ({inst_num})"
            else:
                author_list2 = author_list2 + f"{author}"
            if a < len(authors) - 1:
                author_list2 = author_list2 + ", "
        if debug:
            print(author_list2)
        inst_list = ""
        for i, inst in enumerate(author_insts):
            inst_list = inst_list + f"({i+1}) {inst}"
            if i < len(author_insts) - 1:
                inst_list = inst_list + ", "
        if debug:
            print(inst_list)
    else:
        inst_list = ""

    # Parse other information
    event_daydate = browser.find_element(By.CLASS_NAME, "SlotDate").text
    event_day = re.findall("^[A-Za-z]+", event_daydate)[0]
    event_date = event_daydate.replace(f"{event_day}, ", "")
    event_time = browser.find_element(By.CLASS_NAME, "SlotTime").text.replace(
        " - ", "-"
    )
    location = browser.find_element(By.CLASS_NAME, "propertyInfo").text
    while location[0] == " ":
        location = location[1:]
    if debug:
        print(f"{event_date} ({event_day}) at {event_time} in {location}")

    with open(output_file, "w") as outFile:
        outFile.write(f"#seminar #AGU{thisYear} #AGU\n")
        outFile.write(
            f"Parent session: [[{parent_session_filename}|{parent_session_title}]]\n\n"
        )
        outFile.write(f"# [{title}]({url})\n")
        if author_list2:
            outFile.write(f"{author_list2}\n")
        else:
            print("    (No author list found)")
        outFile.write(f"{inst_list}\n\n")
        outFile.write(f"{event_time} {event_day} {event_date}\n")
        outFile.write(f"{location}\n\n")
        if has_abstract or pl_summary:
            outFile.write("## Description\n")
            if has_abstract:
                outFile.write("### Abstract\n")
                outFile.write(f"{abstract}\n\n")
            if pl_summary:
                outFile.write("### Plain-language summary\n")
                outFile.write(f"{pl_summary}\n")
        outFile.write("\n")
        outFile.write("## Notes\n")
        outFile.write("- \n\n\n")

    return session_urls


def get_session(
    url, browser=None, has_abstract=True
):
    
    if not browser:
        browser = start_browser()

    if debug:
        print("URL: " + url)
    browser.get(url)
    try:
        # WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "finalNumber")))
        WebDriverWait(browser, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "favoriteItem"))
        )
        WebDriverWait(browser, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "field_ParentList_SlotData"))
        )
        WebDriverWait(browser, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "SlotDate"))
        )
        WebDriverWait(browser, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Affiliation"))
        )
        WebDriverWait(browser, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "field_GoodType"))
        )

    except TimeoutException:
        raise RuntimeError(f"Loading took too much time (limit {delay} seconds!")
    time.sleep(5)

    session_code = browser.find_elements(By.CLASS_NAME, "finalNumber")
    if not session_code:
        if "Keynote" in browser.find_element(By.CLASS_NAME, "field_GoodType").text:
            urlsplit = url.split("/")
            session_code = "K" + urlsplit[-1]
        else:
            raise RuntimeError("No session code found (class finalNumber)")
    else:
        session_code = session_code[0].text
    session_title = browser.find_element(By.CLASS_NAME, "favoriteItem").text
    session_title = session_title.replace(session_code + " - ", "")
    print(f"Importing session: {session_title}")
    is_poster = "Poster" in session_title

    # Replace illegal characters for Obsidian filenames
    filename = codetitle_to_filename(session_code, session_title)
    filename_md = filename + ".md"
    output_file = "_" + filename_md
    output_file = truncate_filename(output_file)
    if debug:
        print(f"Filename: {output_file}")

    if path.isfile(output_file):
        if not overwrite:
            print("Won't overwrite existing session file: " + output_file)
            return
        do_replace(output_file)

    session_whenwhere = browser.find_element(By.CLASS_NAME, "field_ParentList_SlotData")
    session_daydate = session_whenwhere.find_element(By.CLASS_NAME, "SlotDate").text
    session_time = session_whenwhere.find_element(By.CLASS_NAME, "SlotTime").text
    session_location = session_whenwhere.find_element(
        By.CLASS_NAME, "propertyInfo"
    ).text
    if debug:
        print(session_daydate)
        print(session_time)
        print(session_location)

    session_abstract = browser.find_element(By.CLASS_NAME, "field_SubTitle").text
    session_abstract = session_abstract.replace("\n", "\n\n")
    session_abstract = session_abstract.replace("\n\n\n", "\n\n")

    session_leaders = browser.find_element(
        By.CLASS_NAME, "field_ChildList_Role"
    ).find_elements(By.CLASS_NAME, "RoleListItem")
    person_names = []
    person_affils_all = []
    person_affils = []
    person_nameaffils = []
    for person in session_leaders:
        person_name = person.find_element(By.TAG_NAME, "a").text
        if person_name in person_names:
            continue
        person_nameaffil = person_name
        person_affil = person.find_elements(By.CLASS_NAME, "Affiliation")
        if not person_affil:
            person_affil = None
        else:
            person_affil = person_affil[0].text.replace("\n", "; ")
            person_nameaffil = person_nameaffil + person_affil
        if person_nameaffil in person_nameaffils:
            continue
        person_nameaffils = person_nameaffils + [person_nameaffil]
        person_names = person_names + [person_name]
        person_affils_all = person_affils_all + [person_affil]
        if person_affil:
            if person_affil not in person_affils:
                person_affils = person_affils + [person_affil]
        # print(f"{person_name} ({person_affil})")
    person_names2 = ""
    for p, person in enumerate(person_names):
        inst = person_affils_all[p]
        if inst:
            inst_num = person_affils.index(inst) + 1
            person_names2 = person_names2 + f"{person} ({inst_num})"
        else:
            person_names2 = person_names2 + f"{person}"
        if p < len(session_leaders) - 1:
            person_names2 = person_names2 + ", "
    affil_list = ""
    for a, affil in enumerate(person_affils):
        affil_list = affil_list + f"({a+1}) {affil}"
        if a < len(person_affils) - 1:
            affil_list = affil_list + ", "
    if person_names2[-2:] == ", ":
        person_names2 = person_names2[:-2]
    if affil_list[-2:] == ", ":
        affil_list = affil_list[:-2]
    if debug:
        print(person_names2)
        print(affil_list)

    # Some sessions (e.g., https://agu.confex.com/agu/fm21/meetingapp.cgi/Session/142602) have no children
    field_ChildList_PaperSlot = browser.find_elements(
        By.CLASS_NAME, "field_ChildList_PaperSlot"
    )
    if field_ChildList_PaperSlot:
        field_ChildList_PaperSlot = field_ChildList_PaperSlot[0]

    if not path.isfile(output_file) or overwrite:
        with open(output_file, "w") as outFile:
            outFile.write(f"#seminar #AGU{thisYear} #AGU\n")
            outFile.write(f"# [{session_title}]({url})\n")
            outFile.write(f"{person_names2}\n")
            outFile.write(f"{affil_list}\n\n")
            outFile.write(f"{session_time} {session_daydate}\n")
            outFile.write(f"{session_location}\n\n")
            outFile.write("## Description\n")
            outFile.write("### Abstract\n")
            outFile.write(f"{session_abstract}\n\n")
            # if pl_summary:
            #     outFile.write("### Plain-language summary\n")
            #     outFile.write(f"{pl_summary}\n")
            outFile.write("\n")
            if field_ChildList_PaperSlot:
                if is_poster:
                    outFile.write("## Posters\n\n")
                    outFile.write("| Pres. author | Title |\n")
                    outFile.write("| ----- | --- |\n")
                else:
                    outFile.write("## Presentations\n\n")
                    outFile.write("| Time | Pres. author | Title |\n")
                    outFile.write("| ---- | ----- | --- |\n")

    is_panel_discussion = False
    if field_ChildList_PaperSlot:
        session_papers = field_ChildList_PaperSlot.find_elements(
            By.CLASS_NAME, "entryInformation"
        )
        for paper in session_papers:
            paper_starttime = paper.find_elements(By.CLASS_NAME, "SlotTime")
            if paper_starttime:
                paper_starttime = paper_starttime[0].text
            else:
                paper_starttime = ""
            paper_number = find_or_none(paper, "SessionListNumber")
            if not paper_number:
                paper_number = f"{session_code}-XX"
            paper_title = paper.find_element(By.CLASS_NAME, "Title").text
            if debug:
                print(f"paper_title: '{paper_title}'")
            paper_presenter = None

            # Panel discussions: Skip moderator and panelists
            # E.g., https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/161615
            if any(x in paper_title for x in ["Moderator:", "Panelist:"]):
                if "\n" in paper_title:
                    paper_title = paper_title.split("\n")[0]
                print(f"Adding {paper_title}")
                with open(output_file, "a") as outFile:
                    if not is_panel_discussion:
                        is_panel_discussion = True
                        outFile.write(f"\n\n## Panel discussion\n")
                        outFile.write(f"### Participants\n")
                    outFile.write(f"- {paper_title}\n")
                continue

            if "\n" in paper_title:
                paper_title_split = paper_title.split("\n")
                paper_title = paper_title_split[0]
                paper_title_split = paper_title_split[1:]
                if debug:
                    print(f"paper_title: '{paper_title}'")
                    print(f"paper_title_split: '{paper_title_split}'")
                paper_presenter = paper_title_split[0]
                if "(Invited)" in paper_title_split:
                    paper_title = paper_title + " (Invited)"
                    paper_title_split.remove("(Invited)")
                ignored_info = None
                if len(paper_title_split) > 1:
                    ignored_info = paper_title_split[1:]
            if not paper_presenter:
                paper_presenter = ""

            paper_title = paper_title.replace(paper_number + " ", "")

            if debug:
                print(f"{paper_title} ({paper_presenter})")
                if ignored_info:
                    print(f"Ignoring extra info: {ignored_info}")

            paper_filename = codetitle_to_filename(paper_number, paper_title)
            paper_filename = truncate_filename(paper_filename + ".md")
            paper_filename = paper_filename[:-3]
            paper_url = paper.find_element(By.TAG_NAME, "a").get_attribute("href")

            if (
                paper_title
                not in [
                    "Introduction",
                    "Conclusions",
                    "Q&A",
                    "Discussion",
                    "Panel Discussion",
                    "Break",
                ]
                and not any(x in paper_title for x in ["Remarks", "Q & A"])
            ):
                paper_3rdcell_text = f"[[{paper_filename}]] ([URL]({paper_url}))"
                try:
                    if not browser2:
                        browser2 = start_browser()
                except:
                    browser2 = start_browser()
                get_presentation(
                    paper_url,
                    [],
                    browser2,
                    title=paper_title,
                    has_abstract=has_abstract,
                )
            else:
                paper_3rdcell_text = paper_title

            paper_cancelled = find_or_none(paper, "cancelled")
            if paper_cancelled:
                if not is_poster:
                    paper_starttime = f"~~{paper_starttime}~~"
                paper_presenter = f"~~{paper_presenter}~~"
                paper_3rdcell_text = f"~~{paper_3rdcell_text}~~"

            if paper_presenter == session_location:
                paper_presenter = ""

            with open(output_file, "a") as outFile:
                if is_poster:
                    outFile.write(f"| {paper_presenter} | {paper_3rdcell_text} |\n")
                else:
                    outFile.write(
                        f"| {paper_starttime} | {paper_presenter} | {paper_3rdcell_text} |\n"
                    )
        try:
            browser2.quit()
        except:
            pass

    with open(output_file, "a") as outFile:
        if is_panel_discussion:
            outFile.write("\n\n### Panel notes\n")
        else:
            outFile.write("\n\n## Session notes\n")
        outFile.write("- \n\n\n")


def translate_ativ_to_confex(url_in):
    tid = re.search(r"tid=(\w+)", url_in)
    if tid:
        tid = tid.group(1)
    else:
        raise RuntimeError(f"No 'tid=' found in URL: {url_in}")
    if tid.startswith("p"):
        kind = "Paper"
    elif "tid=s" in url_in:
        kind = "Session"
    else:
        raise RuntimeError(f"Unrecognized tid: {tid}")
    url_out = f"https://agu.confex.com/agu/agu25/meetingapp.cgi/{kind}/{tid[1:]}"
    if debug:
        print("Converted URL:")
        print(INDENT + f"Was: {url_in}")
        print(INDENT + f"Now: {url_out}")
    return url_out


def main():
    try:
        if not browser:
            browser = start_browser()
    except:
        browser = start_browser()

    for url in sys.argv[1:]:
        # AGU25 scheduler URLs start with this, but they can be translated into the old-style URLs
        if url.startswith("https://eppro01.ativ.me"):
            # Find the word after "tid=" in the url
            url = translate_ativ_to_confex(url)
        else:
            print(f"URL: {url}")

        entrytype = url.split("/")[-2]
        if debug:
            print(f"entrytype: {entrytype}")

        if entrytype == "Session":
            session_url = url
        else:
            session_url = get_presentation(url, [])[0]
        get_session(session_url, browser, has_abstract=True)


if __name__ == "__main__":
    main()
