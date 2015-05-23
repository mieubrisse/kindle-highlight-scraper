### Motivation
Many free tools exist to download your Kindle highlights, but they all require some form of manual input and would be difficult to automate. The provided tool provides a scriptable method for downloading _all_ your Kindle notes as JSON for automated backup, statistics, export to other services, etc. Note that no official API exists, so the information returned is limited to what's available on the "Your Highlights" link reachable from the [Kindle homepage](kindle.amazon.com).

### Installation & Use
1. Install [Easy Install](http://peak.telecommunity.com/DevCenter/EasyInstall#installing-easy-install)
2. Run ``easy_install mechanize``
3. Create a JSON credentials file of the form: `` { "email": "me@gmail.com", "password": "pass123" } ``
4. Restrict permissions of the creds file if you like
5. Run ``extract_kindle_notes.py -c creds.json -o output.json``
    
**Full Usage:**
```
Usage: scrape_kindle_highlights.py [options]

Options:
  -h, --help            show this help message and exit
  -o FILE, --output=FILE
                        filepath to write JSON output to
  -s TYPE, --note-sort=TYPE
                        sort notes within book by: recency, location [default:
                        recency]
  -c FILE, --cred-file=FILE
                        path to JSON file containing Amazon login credentials
                        in the form { email : <email>, password : <password> }
  -e ENCODING, --encoding=ENCODING
                        sets encoding to use when dumping JSON (commonly
                        'utf-8' or 'unicode-escape') [default: utf-8]
  -i JSON_INDENT, --indent-level=JSON_INDENT
                        number of indentation spaces to use when formatting
                        JSON output [default: 4]
  -d, --disable-key-sorting
                        disables sorting of keys in JSON output
```

### Todo
* Refactor into something that's not one enormous file
