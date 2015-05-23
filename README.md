## Motivation
Many free tools exist to download your Kindle notes, but they all require some form of manual input or are difficult to automate. The provided script is an entirely programmatic way of downloading your Kindle highlights and notes as JSON.

## Installation & Use
1. Install [Easy Install](http://peak.telecommunity.com/DevCenter/EasyInstall#installing-easy-install)
2. Run ``easy_install mechanize``
3. Create a credentials file of the form:
``` json
{ email: me@gmail.com, password: pass123 }
```
4. Run ``extract_kindle_notes.py -c creds.json -o outputfile.json``

Full Usage:
```
Usage: scrape_kindle_highlights.py [options]

Options:
  -h, --help            show this help message and exit
  -o FILE, --output=FILE
                        output file to write JSON to
  -s TYPE, --note-sort=TYPE
                        sort notes within book by: recency, location [default:
                        recency]
  -c FILE, --cred-file=FILE
                        path to JSON file containing Amazon login credentials
                        in the form { email : <email>, password : <password> }
  -e ENCODING, --encoding=ENCODING
                        sets Unicode encoding when dumping JSON (see Python
                        codecs for more info) [default: utf-8]
  -i JSON_INDENT, --indent-level=JSON_INDENT
                        sets number of spaces to use when formatting JSON
                        output [default: 4]
  -d, --disable-key-sorting
                        disables sorting of keys in JSON output
```


