import requests
import sys

URL = "http://localhost:3000/"

def main():
    print(f"Fetching {URL}...")
    try:
        r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            html = r.text
            search_str = "grid-cols-1 md:grid-cols-2"
            if search_str in html:
                print(f"SUCCESS: Found '{search_str}' in the served HTML output!")
                sys.exit(0)
            else:
                print(f"WARNING: Did not find '{search_str}' directly in the HTML.")
                print("Note: If the component is lazy-loaded or client-side hydrated only, it might not be in the initial raw index HTML. Let's inspect the page content length.")
                print(f"HTML Length: {len(html)} bytes")
                # Print a small snippet of the body to check
                if "body" in html:
                    body_start = html.find("<body")
                    print("Body snippet:")
                    print(html[body_start:body_start+500])
                sys.exit(1)
        else:
            print(f"Failed to fetch. Status: {r.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
