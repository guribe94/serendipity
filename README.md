# Serendipity

Serendipity recommends nearby places to eat, drink, and explore. The repository
collects the app's backend, its mobile clients, and a few standalone experiments.

## Repository layout

| Path                       | What it is                                                        |
|----------------------------|-------------------------------------------------------------------|
| `serendipity_django/`      | Django backend with Google Places and Yelp search APIs            |
| `serendipity_iOS/`         | Original iOS client (with WatchKit app + extension)               |
| `Serendipity_V2/`          | Second-generation iOS client (with WatchKit app + extension)      |
| `google_place_api_search/` | Standalone Google Places API search script                        |
| `snake_game/`              | Browser-based Snake arcade game (HTML/CSS/JS)                      |
| `tetris/`, `modern_tetris/`| Python (pygame) Tetris — see [`tetris/README.md`](tetris/README.md) |

## Backend

The backend is a Django project. Install dependencies and run it locally:

```bash
pip install -r requirements.txt
python serendipity_django/manage.py runserver
```

Core dependencies (see [`requirements.txt`](requirements.txt)): Django 1.7.4,
geopy, python-google-places, httplib2, and oauth2.

## iOS clients

`serendipity_iOS/` and `Serendipity_V2/` are Xcode projects. Open the
`.xcodeproj` in Xcode and build the `Serendipity` / `SerendipityTest` scheme.
Each ships a companion WatchKit app and extension.

## Standalone games

- **Snake** — open `snake_game/index.html` in any modern browser.
- **Tetris** — `pip install -r tetris/requirements.txt && python -m tetris.main`.

## License

No license has been declared for this repository yet.
