# %%

import glob
import icalendar as ic
import regex as re
import time
from os import path, rename, remove, chdir, makedirs
from datetime import datetime
from zipfile import ZipFile

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

outDir = "/Users/sam/Documents/Dropbox/Apps/Obsidian/Conferences-Workshops-Mtgs/AGU2023"
if not path.exists(outDir):
    makedirs(outDir)
chdir(outDir)

browser = None

def start_browser():
    # prepare the option for the chrome driver
    options = webdriver.ChromeOptions()
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    chrome_driver_binary = "/opt/homebrew/bin/chromedriver"
    # start chrome browser
    # Download other Chromium and Chrome Driver binaries at https://vikyd.github.io/download-chromium-history-version/#/
    browser = webdriver.Chrome(chrome_driver_binary, options=options)
    tz_params = {'timezoneId': 'America/Chicago'}
    browser.execute_cdp_cmd('Emulation.setTimezoneOverride', tz_params)
    return browser

# Parse "summary" into event title and code (if any)
def summary_to_codetitle(summary):
    code = re.findall("[\d\-A-Z]+ - ", summary)
    if code:
        title = summary.replace(code[0], "")
        code = code[0].replace(" - ", "")
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
    for c in ["*", "\"", "\\", "/", "<", ">", ":", "|", "?"]:
        if c in filename:
            raise RuntimeError(f"Illegal character {c} in filename: '{filename}'")
    return filename

def do_replace(output_file):
    old_file = output_file.replace(".md", " "+datetime.now().strftime("%Y%m%d%H%M%S")+".md")
    file_archive = output_file.replace(".md", " ARCHIVE.zip")
    rename(output_file, old_file)
    with ZipFile(file_archive, 'a') as zipObj:
        zipObj.write(old_file)
    remove(old_file)
    
def find_or_none(driver, classname):
    x = driver.find_elements_by_class_name(classname)
    if len(x) > 0:
        x = x[0].text
    else:
        x = None
    return x

def get_presentation(url, session_urls, browser=None, replace=False, title=None, has_abstract=True, author_list2=None):
    if not browser:
        browser = start_browser()
        
    verbose = False
        
    printed_title = False
    if title:
        print(f"Importing presentation: {title}")
        printed_title = True
    
    browser.get(url)
    # time.sleep(5)
    delay = 30 # seconds
    abstract_failed = False
    try:
        WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "field_ParentList_ParentEntries")))
        if has_abstract:
            try:
                WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "field_Abstract")))
            except TimeoutException:
                has_abstract = False
                abstract_failed = True
        if not author_list2:
            WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "RoleListItem")))
    except TimeoutException:
        raise RuntimeError(f"Loading took too much time (limit {delay} seconds! Url: {url}")
    
    # Parent session
    parent = browser.find_element_by_class_name("field_ParentList_ParentEntries")
    tries = 0
    parent2 = None
    while not parent2 and tries < 15:
        tries = tries + 1
        try:
            parent2 = parent.find_element_by_tag_name("a")
        except:
            time.sleep(1)
    if not parent2:
        raise RuntimeError("Parent session info not found!")
    parent_session_code, parent_session_title = summary_to_codetitle(parent2.text)
    parent_session_filename = "_" + codetitle_to_filename(parent_session_code, parent_session_title)
    parent_session_url = parent2.get_property('href')
    if parent_session_url not in session_urls:
        session_urls = session_urls + [parent_session_url]
    if verbose:
        print(f"Parent session: {parent_session_title} ({parent_session_url})")
        print(f"Parent session filename: {parent_session_filename}")
    
    # Parse "summary" into event title and code (if any)
    code, title = summary_to_codetitle(browser.find_element_by_class_name("titleContent").text)
    if not code:
        code = f"{parent_session_code}-XX"
    if not printed_title:
        print(f"Importing presentation: {title}")
    if abstract_failed:
        print("(No abstract found)")
    if verbose:
        print(f"Code: {code}")
        print(f"Title: {title}")
    
    # Replace illegal characters for Obsidian filenames
    filename = codetitle_to_filename(code, title)
    filename_md = filename + ".md"
    # output_file = f"{outDir}/{filename_md}"
    output_file = filename_md
    if verbose:
        print(f"Output file: {output_file}")
    
    if path.isfile(output_file):
        if not replace:
            if verbose:
                print("Returning")
            return session_urls
        else:
            do_replace(output_file)
    if verbose:
        print(f"Filename: {filename}")

    # Abstract
    if has_abstract:
        if verbose:
            print("Getting abstract")
        abstract = browser.find_element_by_class_name("field_Abstract").text.replace("Abstract\n","")
        abstract = abstract.replace("\n", "\n\n")
        abstract = abstract.replace("\n\n\n", "\n\n")
        if verbose:
            print(f"Abstract: {abstract}")
    else:
        abstract = ""

    # P-L Summary
    pl_summary = None
    field_ExtendedAbstract = browser.find_elements_by_class_name("field_ExtendedAbstract")
    if len(field_ExtendedAbstract) > 0:
        pl_summary = field_ExtendedAbstract[0].text.replace("Plain-language Summary\n","")
        pl_summary = pl_summary.replace("\n", "\n\n")
        pl_summary = pl_summary.replace("\n\n\n", "\n\n")
    if verbose:
        print(f'Plain-language summary: {pl_summary}')

    # Authors
    if not author_list2:
        authors = browser.find_elements_by_class_name("RoleListItem")
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
            if a < len(authors)-1:
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
            if a < len(authors)-1:
                author_list2 = author_list2 + ", "
        if verbose:
            print(author_list2)
        inst_list = ""
        for i, inst in enumerate(author_insts):
            inst_list = inst_list + f"({i+1}) {inst}"
            if i < len(author_insts)-1:
                inst_list = inst_list + ", "
        if verbose:
            print(inst_list)
    else:
        inst_list = ""
    
                
    # Parse other information
    event_daydate = (browser.find_element_by_class_name("SlotDate").text)
    event_day = re.findall("^[A-Za-z]+", event_daydate)[0]
    event_date = event_daydate.replace(f"{event_day}, ", "")
    event_time = browser.find_element_by_class_name("SlotTime").text.replace(" - ", "-")
    location = browser.find_element_by_class_name("propertyInfo").text
    while location[0] == " ":
        location = location[1:]
    if verbose:
        print(f"{event_date} ({event_day}) at {event_time} in {location}")
    
    with open(output_file, 'w') as outFile:
        outFile.write("#seminar #AGU2021 #AGU\n")
        outFile.write(f"Parent session: [[{parent_session_filename}|{parent_session_title}]]\n\n")
        outFile.write(f"# [{title}]({url})\n")
        outFile.write(f"{author_list2}\n")
        outFile.write(f"{inst_list}\n\n")
        outFile.write(f"{event_time} {event_day} {event_date}\n")
        outFile.write(f"{location}\n\n")
        outFile.write("## Description\n")
        outFile.write("### Abstract\n")
        outFile.write(f"{abstract}\n\n")
        if pl_summary:
            outFile.write("### Plain-language summary\n")
            outFile.write(f"{pl_summary}\n")
        outFile.write("\n")
        outFile.write("## Notes\n")
        outFile.write("- \n\n\n")
    
    return session_urls

def get_session(url, browser=None, replace=False, get_presentations=False, has_abstract=True):
    if not browser:
        browser = start_browser()
        
    verbose = False
    
    browser.get(url)
    delay = 30 # seconds
    try:
        # WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "finalNumber")))
        WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "favoriteItem")))
        WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "field_ParentList_SlotData")))
        WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "SlotDate")))
        WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "Affiliation")))
        WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, "field_GoodType")))
        
    except TimeoutException:
        raise RuntimeError(f"Loading took too much time (limit {delay} seconds!")
    time.sleep(5)
    
    session_code = browser.find_elements_by_class_name("finalNumber")
    if not session_code:
        if "Keynote" in browser.find_element_by_class_name("field_GoodType").text:
            urlsplit = url.split("/")
            session_code = "K" + urlsplit[-1]
        else:
            raise RuntimeError("No session code found (class finalNumber)")
    else:
        session_code = session_code[0].text
    session_title = browser.find_element_by_class_name("favoriteItem").text
    session_title = session_title.replace(session_code+" - ", "")
    print(f"Importing session: {session_title}")
    is_poster = "Poster" in session_title
    
    # Replace illegal characters for Obsidian filenames
    filename = codetitle_to_filename(session_code, session_title)
    filename_md = filename + ".md"
    # output_file = f"{outDir}/_{filename_md}"
    output_file = "_" + filename_md
    if verbose:
        print(f"Filename: {output_file}")
    
    if path.isfile(output_file):
        if not replace and not get_presentations:
            if verbose:
                print("Returning")
            return
        elif replace:
            do_replace(output_file)
    
    session_whenwhere = browser.find_element_by_class_name("field_ParentList_SlotData")
    session_daydate = session_whenwhere.find_element_by_class_name("SlotDate").text
    session_time = session_whenwhere.find_element_by_class_name("SlotTime").text
    session_location = session_whenwhere.find_element_by_class_name("propertyInfo").text
    if verbose:
        print(session_daydate)
        print(session_time)
        print(session_location)
    
    session_abstract = browser.find_element_by_class_name("field_SubTitle").text
    session_abstract = session_abstract.replace("\n", "\n\n")
    session_abstract = session_abstract.replace("\n\n\n", "\n\n")
    
    session_leaders = browser.find_element_by_class_name("field_ChildList_Role").find_elements_by_class_name("RoleListItem")
    person_names = []
    person_affils_all = []
    person_affils = []
    person_nameaffils = []
    for person in session_leaders:
        person_name = person.find_element_by_tag_name("a").text
        if person_name in person_names:
            continue
        person_nameaffil = person_name
        person_affil = person.find_elements_by_class_name("Affiliation")
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
        if p < len(session_leaders)-1:
            person_names2 = person_names2 + ", "
    affil_list = ""
    for a, affil in enumerate(person_affils):
        affil_list = affil_list + f"({a+1}) {affil}"
        if a < len(person_affils)-1:
            affil_list = affil_list + ", "
    if person_names2[-2:] == ", ":
        person_names2 = person_names2[:-2]
    if affil_list[-2:] == ", ":
        affil_list = affil_list[:-2]
    if verbose:
        print(person_names2)
        print(affil_list)
    
    # Some sessions (e.g., https://agu.confex.com/agu/fm21/meetingapp.cgi/Session/142602) have no children
    field_ChildList_PaperSlot = browser.find_elements_by_class_name("field_ChildList_PaperSlot")
    if field_ChildList_PaperSlot:
        field_ChildList_PaperSlot = field_ChildList_PaperSlot[0] 
    
    if not path.isfile(output_file) or replace:
        with open(output_file, 'w') as outFile:
            outFile.write("#seminar #AGU2021 #AGU\n")
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
    
    if field_ChildList_PaperSlot:
        session_papers = field_ChildList_PaperSlot.find_elements_by_class_name("entryInformation")
        for paper in session_papers:
            paper_starttime = paper.find_elements_by_class_name("SlotTime")
            if paper_starttime:
                paper_starttime = paper_starttime[0].text
            else:
                paper_starttime = ""
            paper_number = find_or_none(paper, "SessionListNumber")
            if not paper_number:
                paper_number = f"{session_code}-XX"
            paper_title = paper.find_element_by_class_name("SessionListTitle").text
            paper_presenter = None
            if "\n" in paper_title:
                paper_title_split = paper_title.split("\n")
                paper_title = paper_title_split[0]
                paper_title_split = paper_title_split[1:]
                paper_presenter = paper_title_split[0]
                if len(paper_title_split) > 1:
                    if len(paper_title_split)==2 and paper_title_split[1]=="(Invited)":
                        paper_title = paper_title + " (Invited)"
                    else:
                        print(paper_title.split("\n"))
                        raise RuntimeError("Error parsing paper title and presenter")
            if not paper_presenter:
                paper_presenter = ""
                
            if verbose:
                print(f"{paper_title} ({paper_presenter})")
            
            paper_filename = codetitle_to_filename(paper_number, paper_title)
            
            paper_url = paper.find_element_by_tag_name("a").get_attribute("href")
            paper_3rdcell_text = f"[[{paper_filename}]] ([URL]({paper_url}))"
            
            if get_presentations and paper_title not in ["Q&A", "Discussion", "Panel Discussion", "The Role of Indigenous Knowledge in Arctic Research", "Plenary - John Kerry - U.S. Special Presidential Envoy For Climate (Virtual)", "Break"] and not "Remarks" in paper_title and not "Q & A" in paper_title:
                try:
                    if not browser2:
                        browser2 = start_browser()
                except:
                    browser2 = start_browser()
                if paper_url == "https://agu.confex.com/agu/fm22/meetingapp.cgi/Paper/1214892":
                    continue
                get_presentation(paper_url, [], browser2, title=paper_title, has_abstract=has_abstract)
            
            paper_cancelled = find_or_none(paper, "cancelled")
            if paper_cancelled:
                if not is_poster:
                    paper_starttime = f"~~{paper_starttime}~~"
                paper_presenter = f"~~{paper_presenter}~~"
                paper_3rdcell_text = f"~~{paper_3rdcell_text}~~"
                # print("CANCELLED")
                
            with open(output_file, 'a') as outFile:
                if is_poster:
                    outFile.write(f"| {paper_presenter} | {paper_3rdcell_text} |\n")
                else:
                    outFile.write(f"| {paper_starttime} | {paper_presenter} | {paper_3rdcell_text} |\n")
        try:
            browser2.quit()
        except:
            pass
            
    with open(output_file, 'a') as outFile:
        outFile.write("\n\n## Session notes\n")
        outFile.write("- \n\n\n")


# %% Import a given URL

url = "https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/157028"
has_abstract = True
author_list2 = ""

try:
    if not browser:
        browser = start_browser()
except:
    browser = start_browser()

# If this schedule entry is a session, save its relative URL for later, then skip
# to the next schedule entry.
entrytype = url.split("/")[-2]
if entrytype == "Session":
    session_url = url
else:
    session_url = get_presentation(url, [], browser, has_abstract=has_abstract, author_list2=author_list2)

get_session(session_url[0], browser)


# %% Import an entire session's presentations

session_url = "https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/157028"
has_abstract = True

try:
    if not browser:
        browser = start_browser()
except:
    browser = start_browser()

get_session(session_url, browser, get_presentations=True, has_abstract=has_abstract)


# %% Import from .ics

if not browser:
    browser = start_browser()

thisDir = "/Users/sam/Documents/Dropbox/2016_KIT/Fire/FURNACES/FFF-Fire_forest_mgmt_Florence/writing/AGU2021/schedule"
session_urls = []
f = 0
for file in glob.glob(f"{thisDir}/*.ics"):
    f = f + 1
    this_ics = open(file, "rb")
    cal = ic.Calendar.from_ical(this_ics.read())
    e = 0
    for component in cal.walk():
        if component.name == "VEVENT":
            e = e + 1
            
            # Get URL and type (Paper or Session) of schedule entry
            uid = component.get("uid").replace(" ","")
            urlid, slot = uid.split("_")
            entrytype = re.findall("^[A-Za-z]+", uid)[0]
            urlid = urlid.replace(entrytype, "")
            url = f"https://agu.confex.com/agu/fm22/meetingapp.cgi/{entrytype}/{urlid}"
            
            # If this schedule entry is a session, save its relative URL for later, then skip
            # to the next schedule entry.
            if entrytype == "Session":
                if url not in session_urls:
                    session_urls = session_urls + [url]
                continue
            
            session_urls = get_presentation( \
                url, session_urls, browser, replace=False)
    this_ics.close()
            
# %% Import a list of sessions

session_urls = ['https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/167650',
                'https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/167727',
                'https://agu.confex.com/agu/fm22/meetingapp.cgi/Session/177101']

for session_url in session_urls:    
    get_session(session_url, browser, get_presentations=True, replace=False)
    
print('Done.')
    
# browser.quit()









