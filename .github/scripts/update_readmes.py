from datetime import datetime
import util


def main():

    listings = util.getListingsFromJSON()

    util.checkSchema(listings)
    job_listings = util.sortListings(listings)

    # create table and embed
    util.embedTable(job_listings, "README.md")

    util.setOutput("commit_message", "Updating READMEs at " + datetime.now().strftime("%B %d, %Y %H:%M:%S"))


if __name__ == "__main__":
    main()
