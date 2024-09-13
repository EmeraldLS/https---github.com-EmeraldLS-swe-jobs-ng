import json
import sys
import uuid
from datetime import datetime
import util
import re

# TODO: fix this object display comment formatting
# ["Company Name", "_No response_", "job Title", "_No response_", "Link to job Posting", "example.com/link/to/posting", "Location", "San Franciso, CA | Austin, TX | Remote"]
LINES = {
    "url": 1,
    "company_name": 3,
    "title": 5,
    "locations": 7,
    "season": 9,
    "active": 13,
    "email": 15,
    "email_is_edit": 17
}

# lines that require special handling
SPECIAL_LINES = set(["url", "locations", "active", "email", "email_is_edit"])

def add_https_to_url(url):
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def getData(body, is_edit, username):
    lines = [text.strip("# ") for text in re.split('[\n\r]+', body)]
    data = {"date_updated": int(datetime.now().timestamp())}

    # url handling
    if "no response" not in lines[ LINES["url"] ].lower():
        data["url"] = add_https_to_url(lines[ LINES["url"] ].strip())

    # location handling
    if "no response" not in lines[ LINES["locations"] ].lower():
        data["locations"] = [line.strip() for line in lines[ LINES["locations"] ].split("|")]

    # active handling
    if "none" not in lines[ LINES["active"] ].lower():
        data["active"] = "yes" in lines[ LINES["active"] ].lower()

    # regular field handling (company_name, etc.)
    for title, line_index in LINES.items():
        if title in SPECIAL_LINES: continue
        content = lines[line_index]

        if "no response" not in content.lower():
            data[title] = content

    # email handling
    if is_edit:
        data["is_visible"] = "[x]" not in lines[15].lower()
    email = lines[ LINES["email_is_edit"] if is_edit else LINES["email"] ].lower()
    if "no response" not in email:
        util.setOutput("commit_email", email)
        util.setOutput("commit_username", username)
    else:
        util.setOutput("commit_email", "action@github.com")
        util.setOutput("commit_username", "GitHub Action")
    
    return data


def main():
    event_file_path = sys.argv[1]

    with open(event_file_path) as f:
        event_data = json.load(f)


    # CHECK IF NEW OR OLD job

    new_job = "new_job" in [label["name"] for label in event_data["issue"]["labels"]]
    edit_job = "edit_job" in [label["name"] for label in event_data["issue"]["labels"]]

    if not new_job and not edit_job:
        util.fail("Only new_job and edit_job issues can be approved")


    # GET DATA FROM ISSUE FORM

    issue_body = event_data['issue']['body']
    issue_user = event_data['issue']['user']['login']

    data = getData(issue_body, is_edit=edit_job, username=issue_user)

    if new_job:
        data["source"] = issue_user
        data["id"] = str(uuid.uuid4())
        data["date_posted"] = int(datetime.now().timestamp())
        data["company_url"] = ""
        data["is_visible"] = True

    # remove utm-source
    utm = data["url"].find("?utm_source")
    if utm == -1:
        utm = data["url"].find("&utm_source")
    if utm != -1:
        data["url"] = data["url"][:utm]


    # UPDATE LISTINGS

    def get_commit_text(listing):
        closed_text = "" if listing["active"] else "(Closed)"
        listing_text = (listing["title"].strip() + " at " + listing["company_name"].strip() + " " + closed_text )
        return listing_text

    with open(".github/scripts/listings.json", "r") as f:
        listings = json.load(f)

    if listing_to_update := next(
        (item for item in listings if item["url"] == data["url"]), None
    ):
        if new_job:
            util.fail("This job is already in our list. See CONTRIBUTING.md for how to edit a listing")
        for key, value in data.items():
            listing_to_update[key] = value

        util.setOutput("commit_message", "updated listing: " + get_commit_text(listing_to_update))
    else:
        if edit_job:
            util.fail("We could not find this job in our list. Please double check you inserted the right url")
        listings.append(data)

        util.setOutput("commit_message", "added listing: " + get_commit_text(data))

    with open(".github/scripts/listings.json", "w") as f:
        f.write(json.dumps(listings, indent=4))


if __name__ == "__main__":
    main()
