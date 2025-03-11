import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import time
from duckduckgo_search import DDGS

def scrape_museums(url):
    """
    Skrapuje podaną stronę i zwraca listę muzeów.
    Elementy znajdują się w <div class="index-card-wrap">.
    Tytuł pobierany jest z <h3 class="title-md content-card-title">,
    a krótki opis z <div class="subtitle-sm content-card-subtitle js-subtitle-content">.
    Dodatkowo pobieramy link (pierwszy <a> z atrybutem href).
    """
    try:
        response = requests.get(url)
    except Exception as e:
        print("Błąd pobierania strony:", e)
        return []

    if response.status_code != 200:
        print("Błąd pobierania strony:", url, "Status code:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    museum_items = soup.find_all('div', class_='index-card-wrap')
    museums = []
    # Znany adres placeholdera, który chcemy pominąć:
    placeholder = "https://assets.atlasobscura.com/assets/blank-f2c3362333e2a7a073648cf7e50aa224b02674cd3b28b24000ca5cdc8980f75f.png"
    
    for item in museum_items:
        # Pobieramy tytuł
        title_tag = item.find('h3', class_='title-md content-card-title')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # Pobieramy krótki opis
        description_tag = item.find('div', class_='subtitle-sm content-card-subtitle js-subtitle-content')
        description = description_tag.get_text(strip=True) if description_tag else "Brak opisu"

        # Pobieramy link (pierwszy tag <a> z atrybutem href)
        link_tag = item.find('a', href=True)
        link = urljoin(url, link_tag['href']) if link_tag else None

        museums.append({
            'title': title,
            'description': description,
            'link': link
        })
    return museums

def get_long_description(url):
    """
    Przechodzi pod podany URL (strona muzeum) i pobiera długi opis.
    Szuka kontenera o selektorze odpowiadającym:
    div.prose.prose-p:aon-body-small.prose-p:text-gray-900.prose-p:mb-4.prose-a:aon-body-link.place-body.max-w-none
    Następnie zbiera tekst ze wszystkich <p>.
    """
    time.sleep(0.03)  # opóźnienie przed pobraniem długiego opisu
    try:
        response = requests.get(url)
    except Exception as e:
        print("Błąd pobierania długiego opisu:", e)
        return None

    if response.status_code != 200:
        print("Błąd pobierania długiego opisu:", url, "Status code:", response.status_code)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    # Używamy CSS selector – znaki ":" trzeba uciec backslashem
    selector = "div.prose.prose-p\\:aon-body-small.prose-p\\:text-gray-900.prose-p\\:mb-4.prose-a\\:aon-body-link.place-body.max-w-none"
    container = soup.select_one(selector)
    if container:
        paragraphs = container.find_all('p')
        long_desc = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        return long_desc
    return None

def get_museum_image(query):
    """
    Wyszukuje obrazek za pomocą DuckDuckGo dla podanego zapytania.
    Zwraca URL pierwszego znalezionego obrazu.
    """
    time.sleep(0.03)  # opóźnienie przed zapytaniem
    try:
        results = DDGS().images(query, max_results=1)
        if results and len(results) > 0:
            return results[0].get("image") or results[0].get("url")
        return None
    except Exception as e:
        print("Błąd pobierania obrazu dla zapytania:", query, e)
    return None

def search_additional_info(query):
    """
    Wykonuje wyszukiwanie za pomocą DuckDuckGo i zwraca pierwszy znaleziony URL.
    """
    time.sleep(0.03)
    try:
        results = DDGS().text(query, max_results=1)
        if results and len(results) > 0:
            return results[0].get("href") or results[0].get("url")
        return None
    except Exception as e:
        print("Błąd wyszukiwania DuckDuckGo dla zapytania:", query, e)
    return None

def sanitize_slug(title):
    """
    Tworzy bezpieczny slug na podstawie tytułu, zastępując niedozwolone znaki.
    """
    slug = title.lower().replace(" ", "-").replace(":", "").replace("?", "").replace("/", "-")
    return slug

def generate_markdown_files(museums, output_dir="site"):
    """
    Generuje strukturę witryny w formacie Markdown:
    - Strona główna (index.md) zawierająca listę pozycji z nagłówkami (##), obrazkami nad krótkimi opisami.
    - Osobna strona Markdown dla każdej pozycji, zawierająca:
      - Tytuł, krótki opis,
      - Długi opis (pobrany z linku muzeum),
      - Obrazek (wyszukany za pomocą DuckDuckGo),
      - Link do oryginalnej strony muzeum,
      - Dodatkowe informacje (link z DuckDuckGo).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generowanie strony głównej (index.md)
    index_content = "# Lista Dziwacznych Muzeów\n\n"
    for museum in museums:
        slug = sanitize_slug(museum['title'])
        index_content += f"## [{museum['title']}]({slug}.md)\n\n"
        
        index_content += f"{museum['description']}\n\n"
        index_content += "---\n\n"
    
    with open(os.path.join(output_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write(index_content)
    
    # Generowanie podstron dla poszczególnych muzeów 
    for museum in museums:
        slug = sanitize_slug(museum['title'])
        page_content = f"# {museum['title']}\n\n"
        page_content += f"**Krótki opis:**\n{museum['description']}\n\n"
        
        # Pobieramy długi opis ze strony muzeum (jeśli link dostępny)
        long_desc = ""
        if museum['link']:
            long_desc = get_long_description(museum['link'])
        if long_desc:
            page_content += "## Szczegółowy opis\n\n" + long_desc + "\n\n"
        else:
            page_content += "## Szczegółowy opis\n\nBrak dodatkowego opisu.\n\n"
        
        # Pobieramy obrazek za pomocą DuckDuckGo
        duck_image = get_museum_image(museum['title'] + " museum")
        if duck_image:
            page_content += f"## Obrazek\n\n![{museum['title']}]({duck_image})\n\n"
        
        # Dodajemy link do oryginalnej strony muzeum
        if museum['link']:
            page_content += f"**Strona muzeum:** [{museum['link']}]({museum['link']})\n\n"
        
        # Dodajemy dodatkowe informacje (link z DuckDuckGo)
        additional_info_url = search_additional_info(museum['title'] + " museum")
        if additional_info_url:
            page_content += f"**Dodatkowe informacje:** [{additional_info_url}]({additional_info_url})\n\n"
        
        file_path = os.path.join(output_dir, f"{slug}.md")
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(page_content)


def main():
    url = "https://www.atlasobscura.com/lists/the-ultimate-list-of-wonderfully-specific-museums"
    print("Rozpoczynam skrapowanie strony:", url)
    museums = scrape_museums(url)
    
    if not museums:
        print("Nie znaleziono żadnych muzeów lub wystąpił błąd podczas scrapowania.")
        return
    
    print(f"Znaleziono {len(museums)} muzeów. Generowanie plików Markdown...")
    generate_markdown_files(museums)
    print("Witryna została wygenerowana w folderze 'site'.")

if __name__ == "__main__":
    main()
