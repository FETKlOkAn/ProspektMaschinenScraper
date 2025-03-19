# Prospektmaschine Scraper

A Python web scraper for extracting brochure/flyer data from prospektmaschine.de. This tool collects information about hypermarket promotional flyers including titles, valid dates, and thumbnail images.

## Features

- Scrapes promotional flyers from German hypermarkets
- Extracts key information including:
  - Flyer title
  - Validity period (from-to dates)
  - Thumbnail image URL
  - Store name
- Saves data in structured JSON format
- Comprehensive logging

## Requirements

- Python 3.6+
- Beautiful Soup 4
- Requests

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the scraper with:

```bash
python3 prospektmaschine_scraper.py
```

The script will:
1. Fetch a list of all hypermarkets
2. Scrape each hypermarket page for brochures
3. Extract and parse brochure data
4. Save the results to `brochures.json`

## Output Format

The output JSON file contains an array of brochure objects, each with the following structure:

```json
{
  "title": "Weekly Offers",
  "thumbnail": "https://www.prospektmaschine.de/path/to/image.jpg",
  "shop_name": "Store Name",
  "valid_from": "2025-03-15",
  "valid_to": "2025-03-21",
  "parsed_time": "2025-03-19 14:30:45"
}
```

## Logging

The scraper logs all activity to both the console and `scraper.log` file, providing detailed information about the scraping process.

## Customization

You can modify the output file name by passing it to the constructor:

```python
scraper = ProspektMaschinenScraper(output_file="custom_filename.json")
scraper.run()
```

## License

[MIT License](LICENSE)

## Disclaimer

This tool is for educational purposes only. Please respect the website's terms of service and robots.txt directives when using this scraper.
