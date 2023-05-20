import csv
import sys
import requests
import json
import time
from SPARQLWrapper import SPARQLWrapper, JSON

def search_book_info_from_google(author_name, book_title):
    url = "https://www.googleapis.com/books/v1/volumes?q=intitle:{}+inauthor:{}".format(book_title, author_name)
    response = requests.get(url)
    while response.status_code != 200:
        time.sleep(1)
        response = requests.get(url)
    data = json.loads(response.text)
    if len(data.get("items", [])) == 0:
        return None
       
    result = data["items"][0]["volumeInfo"]
    for item in data["items"]:
        if result["publishedDate"] > item["volumeInfo"]["publishedDate"]:
            result = item["volumeInfo"]
    print(f"Le livre {book_title} de {author_name} a été trouvé via google.")
    return result

def search_book_info_from_data(author_name,book_title):
    # Query to find the Wikidata ID of the author
    query = """
    PREFIX rdarelationships: <http://rdvocab.info/RDARelationshipsWEMI/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?title ?name ?date ?publisher
    WHERE {
    ?person foaf:name ?name .
    ?oeuvre dcterms:creator ?person .
    ?person foaf:name ?name .
    ?oeuvre dcterms:title ?title .
    ?oeuvre dcterms:date ?date .
    ?edition rdarelationships:workManifested ?oeuvre .
    ?edition dcterms:publisher ?publisher
    FILTER regex(?name, "%s", "i")
    FILTER regex(?title, "%s")
    }
    """ % (author_name, book_title)

    # Send the query and get the results
    sparql = SPARQLWrapper("https://data.bnf.fr/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    data = sparql.query().convert()

    # Return None if no results
    if len(data["results"]["bindings"]) == 0:
        return None

    # Return the first edition (date)
    result = data["results"]["bindings"][0]
    for item in data["results"]["bindings"]:
        if result["date"]["value"] > item["date"]["value"]:
            result = item
    print(f"Le livre {book_title} de {author_name} a été trouvé via bnf.")
    return result

if __name__ == "__main__":
    csv_file = sys.argv[1]
    livres = []
    results = []
    with open(csv_file, newline='', mode='r') as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar="'")
        for row in reader:
            author_name = row[0]
            author_name = author_name.replace(".", "")
            author_name = author_name.split(" ")
            author_name = author_name[-1]
            book_title = row[1]
            book_title = book_title.strip()
            livres.append((author_name, book_title))
            try:
                result = search_book_info_from_data(author_name, book_title)
            except:
                print(f"Une erreur est survenue lors de la recherche du livre {book_title} de {author_name} via bnf.")
            if result is not None:
                info = {
                    "title": result["title"]["value"],
                    "authors": result["name"]["value"],
                    "publishedDate": result["date"]["value"],
                    "edition": result["publisher"]["value"]
                }
            else:
                try:
                    info = search_book_info_from_google(author_name, book_title)
                    if info is None:
                        print(f"Le livre {book_title} de {author_name} n'a pas été trouvé.")
                        continue
                except:
                    print(f"Une erreur est survenue lors de la recherche du livre {book_title} de {author_name} via google.")
                    continue
            results.append(info)

    with open('livres.csv', 'w') as outfile:
        writer = csv.writer(outfile, delimiter=';', quotechar="'")
        # Write the header row
        writer.writerow([
            "authors",
            "title",
            "subtitle",
            "publishedDate",
            "edition"
            "pageCount"
        ])
        for result in results:
            # Save the book info in a CSV file
            # We may not have all the information
            # so we use the get() method to avoid
            # an exception
            writer.writerow([
                result.get("authors", ""),
                result.get("title", ""),
                result.get("subtitle", ""),
                result.get("publishedDate", ""),
                result.get("edition", ""),
                result.get("pageCount", "")
            ])

    # Print percentage of books found
    print("{:.2f}% des livres ont été trouvés.".format(len(results) / len(livres) * 100))
