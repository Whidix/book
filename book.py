import csv
import sys
import requests
import json
import time
from SPARQLWrapper import SPARQLWrapper, JSON

def search_book_info_from_google(author_name, book_title):
    # Construisez l'URL de l'API de Google Books
    url = "https://www.googleapis.com/books/v1/volumes?q=intitle:{}+inauthor:{}&maxResults=1".format(book_title, author_name)

    # Envoyer une requête HTTP GET à l'API de Google Books
    response = requests.get(url)

    # Vérifiez que la requête a réussi
    while response.status_code != 200:
        # Attendre une duree aleatoire
        time.sleep(1)
        response = requests.get(url)

    # Analysez la réponse JSON
    data = json.loads(response.text)

    # Vérifiez si data contient "items"
    if len(data.get("items", [])) == 0:
        return None
    # Obtenez les informations de la première édition
    return data["items"][0]["volumeInfo"]

def search_book_info_from_data(author_name,book_title):
    # Query to find the Wikidata ID of the author
    query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?person ?name ?title ?date
    WHERE {
    ?person foaf:name ?name .
    ?work dcterms:creator ?person .
    ?work dcterms:title ?title .
    ?work dcterms:date ?date .
    FILTER regex(?name, "%s", "i")
    FILTER regex(?title, "%s", "i")
    }
    """ % (author_name, book_title)

    # Send the query and get the results
    sparql = SPARQLWrapper("https://data.bnf.fr/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    # Return None if no results
    if len(results["results"]["bindings"]) == 0:
        return None

    # Return the first edition (date)
    for result in results["results"]["bindings"]:
        # Compare the year

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
            result = search_book_info_from_data(author_name, book_title)
            if result is not None:
                info = {
                    "title": result["title"]["value"],
                    "authors": result["name"]["value"],
                    "publishedDate": result["date"]["value"]
                }
            else:
                info = search_book_info_from_google(author_name, book_title)
                if info is None:
                    print(f"Le livre {book_title} de {author_name} n'a pas été trouvé.")
                    continue
            print(f"Le livre {book_title} de {author_name} a été trouvé.")
            results.append(info)

    with open('livres.csv', 'w') as outfile:
        writer = csv.writer(outfile, delimiter=';', quotechar="'")
        # Write the header row
        writer.writerow([
            "title",
            "subtitle",
            "authors",
            "publishedDate",
            "description",
            "pageCount",
            "categories",
            "industryIdentifiers"
        ])
        for result in results:
            # Save the book info in a CSV file
            # We may not have all the information
            # so we use the get() method to avoid
            # an exception
            writer.writerow([
                result.get("title", ""),
                result.get("subtitle", ""),
                ",".join(result.get("authors", [])),
                result.get("publishedDate", ""),
                result.get("description", ""),
                result.get("pageCount", ""),
                ",".join(result.get("categories", [])),
                result.get("industryIdentifiers", "")
            ])

    # Print percentage of books found
    print("{:.2f}% des livres ont été trouvés.".format(len(results) / len(livres) * 100))
