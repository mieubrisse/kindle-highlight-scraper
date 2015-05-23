#!/usr/bin/python

import mechanize
import re
from bs4 import BeautifulSoup
import json
import urllib
from sys import exit
from optparse import OptionParser
import os
from getpass import getpass
import codecs
import io

# Options parsing constants
OUTPUT_FILEPATH_VAR="output_filepath"
NOTE_SORT_TYPE_VAR="note_sort_type"
CREDS_FILEPATH_VAR="creds_filepath"
ENCODING_VAR="encoding"
JSON_INDENT_VAR="json_indent"
JSON_SORT_KEYS_VAR="json_sort_keys"
EMAIL_CRED_KEY="email"
PASSWORD_CRED_KEY="password"
SORT_NOTES_RECENCY="recency"
SORT_NOTES_LOCATION="location"
SORT_NOTES_CHOICES=[SORT_NOTES_RECENCY, SORT_NOTES_LOCATION]

# Put the rest of the keys here as well
BOOK_HIGHLIGHTS_KEY = "notes"
BOOK_ASIN_KEY = "asin"
BOOK_URL_KEY = "url"
BOOK_AUTHOR_KEY = "author"
BOOK_TITLE_KEY = "title"
HIGHLIGHT_LOCATION_KEY = "location"
HIGHLIGHT_TEXT_KEY = "highlighted_text"
HIGHLIGHT_NOTE_KEY = "note"
HIGHLIGHT_CONTEXT_KEY = "context"

# Web-scraping constants
PARENT_DIV_CLASS = "allHighlightedBooks"
BOOK_DIV_CLASS = "bookMain"
HIGHLIGHT_DIV_CLASS = "highlightRow"
AMAZON_LOGIN_URL = "http://kindle.amazon.com/login"
KINDLE_HOME_URL = "https://kindle.amazon.com"
KINDLE_HIGHLIGHTS_HREF = "/your_highlights"
KINDLE_HIGHLIGHTS_URL = KINDLE_HOME_URL + KINDLE_HIGHLIGHTS_HREF


def parse_options():
    """ Parse command line options and return the options dict """
    sort_notes_opt_help_str="sort notes within book by: " + ", ".join(SORT_NOTES_CHOICES) + " [default: %default]"
    creds_opt_help_str="path to JSON file containing Amazon login credentials in the form { " + EMAIL_CRED_KEY + " : <email>, " + PASSWORD_CRED_KEY + " : <password> }"
    
    parser = OptionParser()
    parser.add_option("-o", "--output", dest=OUTPUT_FILEPATH_VAR, help="filepath to write JSON output to", metavar="FILE")
    parser.add_option("-s", "--note-sort", type="choice", metavar="TYPE", dest=NOTE_SORT_TYPE_VAR, choices=SORT_NOTES_CHOICES, default=SORT_NOTES_RECENCY, help=sort_notes_opt_help_str)
    parser.add_option("-c", "--cred-file", dest=CREDS_FILEPATH_VAR, help=creds_opt_help_str, metavar="FILE")
    parser.add_option("-e", "--encoding", default="utf-8", dest=ENCODING_VAR, help="sets encoding to use when dumping JSON (commonly 'utf-8' or 'unicode-escape') [default: %default]")
    parser.add_option("-i", "--indent-level", type="int", default=4, dest=JSON_INDENT_VAR, help="number of indentation spaces to use when formatting JSON output [default: %default]")
    parser.add_option("-d", "--disable-key-sorting", action="store_false", default=True, dest=JSON_SORT_KEYS_VAR, help="disables sorting of keys in JSON output")
    options, _ =  parser.parse_args()
    return vars(options)

def validate_encoding(encoding):
    try:
        codecs.lookup(encoding)
    except (LookupError, TypeError):
        print "Error: Invalid encoding '{0}'".format(encoding)
        exit(1)

def validate_output_filepath(output_filepath):
    """ 
    Tries to write a testfile to the user's desired output location and exits the script if it cannot
    NOTE: This will squash anything that exists at the given location currently
    """
    try:
        output_fp = open(output_filepath, 'w')
        output_fp.close()
    except IOError:
        print "Error: Cannot open output filepath '{0}' for writing".format(output_filepath)
        exit(1)
    if not os.path.isfile(output_filepath):
        print "Error: Could not write test file to output location '{0}'".format(output_filepath)
        exit(1)
    try:
        os.remove(output_filepath)
    except IOError:
        print "Error: Removing test file at output filepath '{0}' failed".format(output_filepath)
        exit(1)

def extract_credentials(options):
    """ 
    Gets the user's Amazon email/password combination, either from user input or from a creds file 
    Return - tuple of (email, password)
    """
    if options[CREDS_FILEPATH_VAR] is None:
        need_creds = True
        while need_creds:
            email = raw_input("Email: ")
            password = getpass("Password: ")
            if email is None or password is None or len(email.strip()) == 0 or len(password.strip()) == 0: 
                print "Invalid email/password; try again"
            else:
                need_creds = False
        return (email, password)
    else:
        creds_filepath = options[CREDS_FILEPATH_VAR]
        if not os.path.isfile(creds_filepath):
            print "Error: No creds file found at " + creds_filepath
            exit(1)
        creds_fp = open(creds_filepath, 'r')
        try:
            creds = json.load(creds_fp)
        except ValueError:
            print "Error: Creds file is not valid JSON"
            exit(1)
        if EMAIL_CRED_KEY not in creds or PASSWORD_CRED_KEY not in creds:
            print "Error: Could not find email/password keys in cred JSON"
            exit(1)
        email = creds[EMAIL_CRED_KEY]
        password = creds[PASSWORD_CRED_KEY]
        return (email, password)

def initialize_browser():
    """ Returns the browser after initialization """
    browser = mechanize.Browser()
    browser.set_handle_robots(False)
    browser.set_handle_redirect(True)
    browser.addheaders = [("User-agent", "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13")]
    return browser

def strip_invalid_html(html):
    """ The responses Amazon gives back don't pass the Python HTML parser, so we need to do some processing on them """
    # The initial HTML we get has malformed headers
    doctype_stripped = re.sub('<!DOCTYPE[^>]*>', '', html)
    return re.sub('\\\\', '', doctype_stripped)

def perform_kindle_login(browser, email, password):
    """ 
    Log in to Amazon Kindle using the provided email and passwords and exit if login fails
    """
    # Login to Amazon
    browser.open(AMAZON_LOGIN_URL)
    bugged_response = browser.response().get_data()
    doctype_stripped = re.sub('<!DOCTYPE[^>]*>','', bugged_response)
    incorrect_backslashes_stripped = re.sub('\\\\', '', doctype_stripped)
    correct_response = mechanize.make_response(incorrect_backslashes_stripped, [("Content-Type", "text/html")], AMAZON_LOGIN_URL, 200, "OK")
    browser.set_response(correct_response)
    browser.select_form(name="signIn")
    browser["email"] = email
    browser["password"] = password

    login_response =  browser.submit()
    if login_response.code >= 400:
        print "Error: Failed to log in to " + AMAZON_LOGIN_URL
        exit(1)
    login_html = strip_invalid_html(login_response.get_data())
    soup = BeautifulSoup(login_html)
    # Amazon doesn't use response codes or data to indicate errors... it uses HTML, built on the backend :|
    if len(soup.select("div.message.error")) != 0:
        print "Error: Failed to log in to " + AMAZON_LOGIN_URL
        exit(1)

def load_highlights_page(browser):
    """ 
    Loads the page with your Kindle highlights and returns the URL 
    Return - response object from browser opening page
    """
    # For some reason, you can't navigate to the page directly and you have to go through kindle.amazon.com
    browser.open(KINDLE_HOME_URL)
    # This is relatively fragile, and relies on a link that points to the 'KINDLE_HIGHLIGHTS_HREF' value
    your_highlights_link = browser.find_link(url=KINDLE_HIGHLIGHTS_HREF)
    return browser.follow_link(your_highlights_link)

def initialize_elements_to_process(html):
    """
    Initializes the emulated state of the Javascript frontend: elements to process, asins that have already been seen, and the mysterious offset tag that the backend somehow uses
    Return - triple of (BeautifulSoup tags to process, list of the one ASIN that's loaded now, and the offset that came with the ASIN)
    """

    corrected_html = strip_invalid_html(html)

    soup = BeautifulSoup(corrected_html)
    tags_to_process = soup.select("#{0} > div".format(PARENT_DIV_CLASS))
    
    # One book will be loaded to start, so - like Amazon does - we need to initialize the offset and used_asins from there
    initial_book_tag = soup.select("#{0} > div.{1}".format(PARENT_DIV_CLASS, BOOK_DIV_CLASS))[0]
    initial_book_asin, initial_offset = initial_book_tag["id"].split("_")
    return (tags_to_process, [initial_book_asin], initial_offset)

def load_more_elements_to_process(browser, used_asins, offset):
    """
    Emulates the addNextBook Javascript function called when the user approaches the bottom of the Kindle highlights page
    This function generates HTML on the backend (why is it being built on the backend???), then sends it to the frontend which will drop it into the DOM
    We hit the same endpoint to get the new piece of HTML that should be inserted, then pull out the new highlight tags with Beautiful Soup
    This is necessary because not all books are shown on pageload
    Return - triple of (new BeautifulSoup tags loaded, ASIN of new book, new offset to use)
    """
    params = {
            "current_offset" : offset,
            "used_asins[]" : used_asins,
            "upcoming_asins[]" : ""       # Unused, as far as I can tell
            }
    encoded_params = urllib.urlencode(params, True)  # Amazon uses the doseq style
    request = mechanize.Request(KINDLE_HIGHLIGHTS_URL + "/next_book?" + encoded_params)
    request.add_header("Referer", KINDLE_HIGHLIGHTS_URL)
    response = browser.open(request)
    response_data = response.get_data()
    if len(response_data.strip()) == 0:
        return ([], used_asins, offset) # No more books
    soup = BeautifulSoup(response.read())
    """
    def filter_func(tag): 
        tag_classes = tag["class"]
        return tag.name == "div" and (BOOK_DIV_CLASS in tag_classes or HIGHLIGHT_DIV_CLASS in tag_classes)
    """
    new_elements = soup.select("> div")    # Get top-level divs which will be the nodes we want
    new_book_tag = soup.select("div." + BOOK_DIV_CLASS)[0]
    new_book_asin, new_offset = new_book_tag["id"].split("_")
    return (new_elements, new_book_asin, new_offset)

def scrape_highlight_elements_from_page(response, browser):
    """ Given the response of loading the highlights page, builds a list of Beautiful Soup tags that need to be processed into JSON """
    
    initial_html = response.get_data()
    elements_to_process, used_asins, offset = initialize_elements_to_process(initial_html)
    
    books_remaining=True
    while books_remaining:
        new_elements, new_asin, new_offset = load_more_elements_to_process(browser, used_asins, offset)
        if len(new_elements) == 0:
            books_remaining = False
        else:
            elements_to_process.extend(new_elements)
            used_asins.append(new_asin)
            offset = new_offset
    
    return elements_to_process


def extract_book_info(book_tag, url):
    """Extracts info about a book containing highlights from the HTML Amazon uses to represent it"""
    new_book = {}
    # We have to do this because for some reason, the back end sends the "offset" information to the front end via the ID of the book div
    book_asin = book_tag["id"].split("_")[0]
    new_book[BOOK_ASIN_KEY] = book_asin
    
    # Extract title and book URL
    title_tags = book_tag.select("span.title > a")
    if len(title_tags) > 0:
        title_tag = title_tags[0]
        try:
            new_book[BOOK_URL_KEY] = url + title_tag["href"]
        except KeyError:
            pass
        # Is it possible for a book to lack a title here?
        new_book[BOOK_TITLE_KEY] = title_tag.string.strip()
    else:
        print "Warning: No title span element found for book with ASIN " + book_asin
    
    # Extract author
    author_tags = book_tag.select("span.author")
    if len(author_tags) > 0:
        author_tag = author_tags[0]
        author_str = author_tag.string.strip()
        attribution_str = "by "
        if author_str.startswith(attribution_str):
            new_book[BOOK_AUTHOR_KEY] = author_str[len(attribution_str):]
        else:
            new_book[BOOK_AUTHOR_KEY] = author_str
    else:
        print "Warning: No author span element found for book with ASIN " + book_asin
    
    new_book[BOOK_HIGHLIGHTS_KEY] = []
    return new_book

def extract_highlight_info(highlight_tag, book_asin):
    """Extracts info about a highlighted section of text from the HTML Amazon uses to represent it"""
    new_highlight = {}
    
    # Extract highlight location
    location_tags = highlight_tag.select("a.readMore")
    highlight_location = None
    if len(location_tags) > 0:
        location_tag = location_tags[0]
        link_text = location_tag.string.strip()
        match_text = re.search('\d+$', link_text).group()
        if match_text is None:
            print "Warning: Missing highlight location number for highlight for book ASIN: " + book_asin
        else:
            highlight_location = int(match_text)
            new_highlight[HIGHLIGHT_LOCATION_KEY] = highlight_location
    else:
        print "Warning: Missing highlight location span for highlight for book ASIN: " + book_asin
    
    # Extract highlighted text; if missing, the note will have 'context' instead
    highlighted_text_tags = highlight_tag.select("span.highlight")
    if len(highlighted_text_tags) > 0:
        highlighted_text_tag = highlighted_text_tags[0]
        new_highlight[HIGHLIGHT_TEXT_KEY] = highlighted_text_tag.string.strip()
    else:
        context_tags = highlight_tag.select("span.context")
        if len(context_tags) > 0:
            context_tag = context_tags[0]
            new_highlight[HIGHLIGHT_CONTEXT_KEY] = context_tag.string.strip()
        else:
            if highlight_location is None:
                print "Warning: No highlighted text or context span elements found for highlight for book with ASIN: " + book_asin
            else:
                print "Warning: No highlighted text or context span elements found for highlight at location " + str(highlight_location)
    
    # Extract note text
    note_content_tags = highlight_tag.select("span.noteContent")
    if len(note_content_tags) > 0:
        note_content_tag = note_content_tags[0]
        note_content = note_content_tag.string
        if not (note_content is None or len(note_content.strip()) == 0):
            new_highlight[HIGHLIGHT_NOTE_KEY] = note_content_tag.string.strip(' \n"')
    else:
        print "Warning: Skipping adding note content because len is " + str(len(note_content_tags))
    
    return new_highlight


def build_books_list(tags_to_process, highlights_url):
    """
    Processes the given list of BeautifulSoup tags into a list of books containing notes that can be outputted and/or written to file
    Return - a list of book objects of the following form:
    {
        asin
        title
        url
        author
        notes : [ {
            highlighted_text OR context (if no highlighted text present)
            note (optional)
            location
        } ... ]
    }
    """
    books = []
    current_book = None
    for tag in tags_to_process:
        tag_classes = tag["class"]
        if BOOK_DIV_CLASS in tag_classes:
            current_book = extract_book_info(tag, highlights_url)
            books.append(current_book)
        elif HIGHLIGHT_DIV_CLASS in tag_classes:
            if current_book is None:
                print "Error: Skipping note because parent book doesn't have an ID"
            else:
                current_book[BOOK_HIGHLIGHTS_KEY].append(extract_highlight_info(tag, current_book[BOOK_ASIN_KEY]))
        else:
            print "Skipping unrecognized tag: \n" + str(tag)
    
    return books

def dump_json(json_input, options):
    """ Encapsulate the JSON-formatting logic """
    encoding = options[ENCODING_VAR]
    indent_level = options[JSON_INDENT_VAR]
    sort_keys = options[JSON_SORT_KEYS_VAR]
    if encoding == 'unicode-escape':
        return json.dumps(json_input, indent=indent_level, sort_keys=sort_keys, ensure_ascii=True)
    else:
        # We do the following because sometimes the json library in Python 2 will write a mix of Unicode and str objects as per here:
        # http://stackoverflow.com/questions/18337407/saving-utf-8-texts-in-json-dumps-as-utf8-not-as-u-escape-sequence
        return unicode(json.dumps(json_input, indent=indent_level, sort_keys=sort_keys, ensure_ascii=False)).encode(encoding)

if __name__ == "__main__":
    # Deal with options
    options = parse_options()
    validate_encoding(options[ENCODING_VAR])
    if options[OUTPUT_FILEPATH_VAR] is not None:
        has_output_filepath = True
        validate_output_filepath(options[OUTPUT_FILEPATH_VAR])
    else:
        has_output_filepath = False
    email, password = extract_credentials(options)

    # Scrape data from Amazon's Kindle site
    browser  = initialize_browser()
    perform_kindle_login(browser, email, password)
    loading_response = load_highlights_page(browser)
    tags_to_process =  scrape_highlight_elements_from_page(loading_response, browser)
    highlighted_books = build_books_list(tags_to_process, KINDLE_HOME_URL)

    # Output highlighted books
    if has_output_filepath:
        with open(options[OUTPUT_FILEPATH_VAR], 'w') as fp:
            fp.write(dump_json(highlighted_books, options))
    else:
        # We don't use the json module's encoding because the ensure_ascii flag is buggy (see documentation for write_books_to_file)
        print dump_json(highlighted_books, options)
