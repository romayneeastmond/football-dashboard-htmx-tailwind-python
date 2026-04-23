# Football Scores & Standings Dashboard

A modern, responsive football dashboard built with **Flask**, **HTMX**, and **Tailwind CSS**. This application scrapes real-time data from ESPN (via stable API endpoints) to provide up-to-date league standings, upcoming fixtures, and match results.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)
![HTMX](https://img.shields.io/badge/HTMX-1.9-3D55EE?style=for-the-badge&logo=htmx&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.0-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

## 🚀 Features

- **Live Standings**: Real-time position tables for major European leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1) and the CPL.
- **Qualification Zones**: Visual indicators for UCL, UEL, and Relegation zones.
- **HTMX Powered**: Smooth, asynchronous content loading for fixtures and results without full page reloads.
- **Instant Search**: Real-time team filtering with an autocomplete-style dropdown.
- **Dark Mode**: Sleek night-mode support with local storage persistence.
- **Robust Scraping**: Implementation of ESPN API-based data fetching to ensure high availability and bypass common cloud/WAF restrictions.
- **Mobile Responsive**: Fully optimized for all screen sizes using Tailwind CSS.

## 🛠️ Tech Stack

- **Backend**: Python / Flask
- **Frontend**: HTMX, Tailwind CSS, Jinja2
- **Data Source**: ESPN (via internal JSON APIs and BeautifulSoup)
- **Deployment**: Optimized for Azure Web Apps and local environments

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/football-dashboard.git
   cd football-dashboard
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```
   The app will be available at `http://localhost:5001`.

## 📂 Project Structure

- `app.py`: Main Flask application and routing logic.
- `scrape_standings.py`: Logic for fetching and parsing league standings.
- `scrape_upcoming.py` / `scrape_results.py`: Modules for match data.
- `scrape_cpl.py`: Specialized scraper for the Canadian Premier League API.
- `templates/`: Jinja2 templates (including `index.html` and HTMX partials).
- `static/`: CSS and image assets.

## 🛡️ Best Practices Implemented

- **Graceful Error Handling**: Automatically filters and hides leagues or sections if data source is unavailable.
- **Performance**: Uses HTMX `load` triggers to defer heavy scraping tasks until after the initial page load.
- **Security**: Implements realistic browser headers to ensure stable communication with data providers.

## 📄 License

This project is open-source and available under the **MIT License**. Feel free to use, modify, and distribute it as you see fit.

---
*Created for portfolio demonstration purposes.*
