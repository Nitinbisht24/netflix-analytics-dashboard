# -*- coding: utf-8 -*-
"""
_build_engagement_csv.py
─────────────────────────────────────────────────────────────────────────────
One-off generator script for `netflix_engagement_report.csv`.

Every row below is compiled from PUBLIC, REAL data published by Netflix in
its bi-annual "What We Watched: A Netflix Engagement Report" series (and
the "Most Popular" all-time lists on Tudum/Wikipedia), cross-checked against
trade press coverage (Variety, TV Guide, Digital Trends, NME, TV Blackbox,
What's-on-Netflix, nScreenMedia). No figures are invented — where a metric
was not published or could not be confirmed, the field is left blank (NULL)
rather than estimated.

This script is kept in the repo for provenance/transparency. It is NOT
imported by the application; it only produces the static CSV checked into
data/raw/. Re-running it just regenerates the same file.

Sources (see data/DATA_DICTIONARY.md for full citation list):
  - about.netflix.com "What We Watched" H1 2023 .. H2 2025 releases
  - en.wikipedia.org "List of most-watched Netflix original programming"
  - Variety, TV Guide, Digital Trends, NME, TV Blackbox, What's-on-Netflix,
    nScreenMedia reporting on each report's release
"""
import csv
import os

# Columns:
# title, content_type, primary_genre, genre_detail, country_origin, language,
# report_period, premiere_date, hours_viewed_millions, views_millions, source

ROWS = [
    # ── ALL-TIME TOP 10 MOVIES (Wikipedia "Most popular Netflix movies") ──
    ("KPop Demon Hunters", "Movie", "Animation", "Musical fantasy action", "United States", "English", "All-Time", "2025-06-20", 541.8, 325.1, "Wikipedia: Most-watched Netflix programming"),
    ("Red Notice", "Movie", "Action", "Action comedy", "United States", "English", "All-Time", "2021-11-12", 454.2, 230.9, "Wikipedia: Most-watched Netflix programming"),
    ("Carry-On", "Movie", "Thriller", "Action thriller", "United States", "English", "All-Time", "2024-12-13", 344.1, 172.1, "Wikipedia: Most-watched Netflix programming"),
    ("Don't Look Up", "Movie", "Science Fiction", "Satirical science fiction", "United States", "English", "All-Time", "2021-12-24", 408.6, 171.4, "Wikipedia: Most-watched Netflix programming"),
    ("The Adam Project", "Movie", "Science Fiction", "Science fiction adventure", "United States", "English", "All-Time", "2022-03-11", 281.0, 157.6, "Wikipedia: Most-watched Netflix programming"),
    ("Bird Box", "Movie", "Horror", "Horror thriller", "United States", "English", "All-Time", "2018-12-21", 325.3, 157.4, "Wikipedia: Most-watched Netflix programming"),
    ("Back in Action", "Movie", "Action", "Action comedy", "United States", "English", "All-Time", "2025-01-17", 279.7, 147.2, "Wikipedia: Most-watched Netflix programming"),
    ("Leave the World Behind", "Movie", "Thriller", "Apocalyptic thriller", "United States", "English", "All-Time", "2023-12-08", 339.3, 143.4, "Wikipedia: Most-watched Netflix programming"),
    ("The Gray Man", "Movie", "Action", "Action thriller", "United States", "English", "All-Time", "2022-07-22", 299.5, 139.3, "Wikipedia: Most-watched Netflix programming"),
    ("Damsel", "Movie", "Fantasy", "Fantasy action adventure", "United States", "English", "All-Time", "2024-03-08", 253.0, 138.0, "Wikipedia: Most-watched Netflix programming"),

    # ── ALL-TIME TOP 10 TV (Wikipedia "Most popular Netflix television series") ──
    ("Squid Game (Season 1)", "TV Show", "Thriller", "Survival drama", "South Korea", "Korean", "All-Time", None, 2205.2, 265.2, "Wikipedia: Most-watched Netflix programming"),
    ("Wednesday (Season 1)", "TV Show", "Comedy", "Supernatural mystery comedy", "United States", "English", "All-Time", None, 1718.8, 252.1, "Wikipedia: Most-watched Netflix programming"),
    ("Squid Game (Season 2)", "TV Show", "Thriller", "Survival drama", "South Korea", "Korean", "All-Time", "2024-12-26", 1380.1, 192.6, "Wikipedia: Most-watched Netflix programming"),
    ("Squid Game (Season 3)", "TV Show", "Thriller", "Survival drama", "South Korea", "Korean", "All-Time", "2025-06-27", 894.3, 145.8, "Wikipedia: Most-watched Netflix programming"),
    ("Adolescence", "TV Show", "Drama", "Coming-of-age drama (limited series)", "United Kingdom", "English", "All-Time", None, 546.5, 142.6, "Wikipedia: Most-watched Netflix programming"),
    ("Stranger Things (Season 4)", "TV Show", "Science Fiction", "Sci-fi horror", "United States", "English", "All-Time", None, 1838.0, 140.7, "Wikipedia: Most-watched Netflix programming"),
    ("Stranger Things (Season 5)", "TV Show", "Science Fiction", "Sci-fi horror", "United States", "English", "All-Time", "2025-11-26", 1391.3, 133.8, "Wikipedia: Most-watched Netflix programming"),
    ("Wednesday (Season 2)", "TV Show", "Comedy", "Supernatural mystery comedy", "United States", "English", "All-Time", None, 928.5, 119.3, "Wikipedia: Most-watched Netflix programming"),
    ("Monster (Season 1)", "TV Show", "Crime", "True crime drama", "United States", "English", "All-Time", None, 1031.1, 115.6, "Wikipedia: Most-watched Netflix programming"),
    ("Bridgerton (Season 1)", "TV Show", "Romance", "Period romance drama", "United States", "English", "All-Time", None, 929.3, 113.3, "Wikipedia: Most-watched Netflix programming"),

    # ── 2023-H1 (Engagement Report #1, Jan-Jun 2023) ──
    ("The Mother", "Movie", "Action", "Action thriller", "United States", "English", "2023-H1", None, 249.9, None, "Netflix Engagement Report H1 2023"),
    ("Luther: The Fallen Sun", "Movie", "Crime", "Crime thriller", "United Kingdom", "English", "2023-H1", None, 209.7, None, "Netflix Engagement Report H1 2023"),
    ("Extraction 2", "Movie", "Action", "Action thriller", "United States", "English", "2023-H1", None, 201.8, None, "Netflix Engagement Report H1 2023"),
    ("You People", "Movie", "Comedy", "Romantic comedy", "United States", "English", "2023-H1", None, 181.8, None, "Netflix Engagement Report H1 2023"),
    ("Murder Mystery 2", "Movie", "Comedy", "Comedy mystery", "United States", "English", "2023-H1", None, 173.6, None, "Netflix Engagement Report H1 2023"),

    # ── 2023-H2 (Engagement Report #2, Jul-Dec 2023) ──
    ("Leave the World Behind", "Movie", "Thriller", "Apocalyptic thriller", "United States", "English", "2023-H2", "2023-12-08", None, 121.0, "Netflix Engagement Report H2 2023"),
    ("Heart of Stone", "Movie", "Action", "Action thriller", "United States", "English", "2023-H2", None, None, 109.6, "Netflix Engagement Report H2 2023"),
    ("Leo", "Movie", "Animation", "Animated comedy", "United States", "English", "2023-H2", None, None, 96.0, "Netflix Engagement Report H2 2023"),
    ("Nowhere", "Movie", "Thriller", "Survival thriller", "Spain", "Spanish", "2023-H2", None, None, 86.2, "Netflix Engagement Report H2 2023"),
    ("The Out-Laws", "Movie", "Comedy", "Action comedy", "United States", "English", "2023-H2", None, None, 83.8, "Netflix Engagement Report H2 2023"),
    ("Best. Christmas. Ever!", "Movie", "Comedy", "Holiday comedy", "United States", "English", "2023-H2", None, None, 45.7, "Netflix Engagement Report H2 2023"),
    ("Dr. Seuss' The Grinch", "Movie", "Animation", "Animated family", "United States", "English", "2023-H2", None, None, 45.3, "Netflix Engagement Report H2 2023"),
    ("The Super Mario Bros. Movie", "Movie", "Animation", "Animated adventure (licensed)", "United States", "English", "2023-H2", None, None, 44.9, "Netflix Engagement Report H2 2023"),
    ("One Piece (Season 1)", "TV Show", "Adventure", "Action adventure", "United States", "English", "2023-H2", None, None, 71.6, "Netflix Engagement Report H2 2023"),
    ("Dear Child", "TV Show", "Thriller", "Psychological thriller", "Germany", "German", "2023-H2", None, None, 52.5, "Netflix Engagement Report H2 2023"),
    ("Forgotten Love", "Movie", "Romance", "Romantic drama", "Poland", "Polish", "2023-H2", None, None, 43.0, "Netflix Engagement Report H2 2023"),
    ("Pact of Silence", "TV Show", "Crime", "Crime drama", "Mexico", "Spanish", "2023-H2", None, None, 21.0, "Netflix Engagement Report H2 2023"),
    ("Mask Girl", "TV Show", "Thriller", "Thriller drama", "South Korea", "Korean", "2023-H2", None, None, 19.0, "Netflix Engagement Report H2 2023"),
    ("Yu Yu Hakusho", "TV Show", "Animation", "Anime action fantasy", "Japan", "Japanese", "2023-H2", None, None, 17.0, "Netflix Engagement Report H2 2023"),
    ("Berlin", "TV Show", "Crime", "Heist crime drama", "Spain", "Spanish", "2023-H2", None, None, 11.0, "Netflix Engagement Report H2 2023"),
    ("The Railway Men", "TV Show", "Drama", "Historical drama", "India", "Hindi", "2023-H2", None, None, 11.0, "Netflix Engagement Report H2 2023"),
    ("Suits", "TV Show", "Drama", "Legal drama (licensed, 9 seasons)", "United States", "English", "2023-H2", None, None, 144.0, "Netflix Engagement Report H2 2023"),
    ("Young Sheldon", "TV Show", "Comedy", "Sitcom (licensed)", "United States", "English", "2023-H2", None, None, 88.0, "Netflix Engagement Report H2 2023"),
    ("Grey's Anatomy", "TV Show", "Drama", "Medical drama (licensed)", "United States", "English", "2023-H2", None, None, 51.0, "Netflix Engagement Report H2 2023"),
    ("Gossip Girl", "TV Show", "Drama", "Teen drama (licensed)", "United States", "English", "2023-H2", None, None, 49.0, "Netflix Engagement Report H2 2023"),
    ("Gilmore Girls", "TV Show", "Comedy", "Comedy drama (licensed)", "United States", "English", "2023-H2", None, None, 45.0, "Netflix Engagement Report H2 2023"),
    ("Gabby's Dollhouse", "TV Show", "Family", "Kids animation", "United States", "English", "2023-H2", None, None, 90.0, "Netflix Engagement Report H2 2023"),
    ("Family Switch", "Movie", "Comedy", "Family comedy", "United States", "English", "2023-H2", None, None, 62.0, "Netflix Engagement Report H2 2023"),
    ("The Monkey King", "Movie", "Animation", "Animated fantasy", "United States", "English", "2023-H2", None, None, 43.0, "Netflix Engagement Report H2 2023"),
    ("Is It Cake?", "TV Show", "Reality", "Reality competition", "United States", "English", "2023-H2", None, None, 21.0, "Netflix Engagement Report H2 2023"),
    ("Love Is Blind", "TV Show", "Reality", "Reality dating", "United States", "English", "2023-H2", None, None, 20.0, "Netflix Engagement Report H2 2023"),
    ("The Ultimatum: Marry or Move On", "TV Show", "Reality", "Reality dating", "United States", "English", "2023-H2", None, None, 12.0, "Netflix Engagement Report H2 2023"),
    ("World War II: From the Frontlines", "TV Show", "Documentary", "War documentary", "United States", "English", "2023-H2", None, None, 13.0, "Netflix Engagement Report H2 2023"),
    ("Lupin (Parts 1-3)", "TV Show", "Crime", "Heist crime drama", "France", "French", "2023-H2", None, None, 100.0, "Netflix Engagement Report H2 2023"),
    ("CoComelon (All Seasons)", "TV Show", "Family", "Kids animation", "United States", "English", "2023-H2", None, None, 200.0, "Netflix Engagement Report H2 2023"),
    ("The Witcher (All Seasons)", "TV Show", "Fantasy", "Fantasy drama", "United States", "English", "2023-H2", None, None, 76.0, "Netflix Engagement Report H2 2023"),
    ("Virgin River (All Seasons)", "TV Show", "Romance", "Romance drama", "United States", "English", "2023-H2", None, None, 69.0, "Netflix Engagement Report H2 2023"),
    ("The Crown (All Seasons)", "TV Show", "Drama", "Historical drama", "United Kingdom", "English", "2023-H2", None, None, 50.0, "Netflix Engagement Report H2 2023"),
    ("Sweet Magnolias", "TV Show", "Drama", "Drama", "United States", "English", "2023-H2", None, None, 35.0, "Netflix Engagement Report H2 2023"),
    ("Top Boy", "TV Show", "Crime", "Crime drama", "United Kingdom", "English", "2023-H2", None, None, 26.0, "Netflix Engagement Report H2 2023"),
    ("Heartstopper", "TV Show", "Romance", "Teen romance", "United Kingdom", "English", "2023-H2", None, None, 24.0, "Netflix Engagement Report H2 2023"),
    ("Sintonia", "TV Show", "Drama", "Drama", "Brazil", "Portuguese", "2023-H2", None, None, 20.0, "Netflix Engagement Report H2 2023"),
    ("Sweet Home", "TV Show", "Horror", "Horror thriller", "South Korea", "Korean", "2023-H2", None, None, 17.0, "Netflix Engagement Report H2 2023"),

    # ── 2024-H1 (Engagement Report #3, Jan-Jun 2024) ──
    ("Fool Me Once", "TV Show", "Thriller", "Mystery thriller", "United Kingdom", "English", "2024-H1", None, None, 108.0, "Netflix Engagement Report H1 2024"),
    ("Baby Reindeer", "TV Show", "Drama", "Drama (limited series)", "United Kingdom", "English", "2024-H1", None, None, 88.0, "Netflix Engagement Report H1 2024"),
    ("The Gentlemen", "TV Show", "Crime", "Crime comedy", "United Kingdom", "English", "2024-H1", None, None, 76.0, "Netflix Engagement Report H1 2024"),
    ("One Day", "TV Show", "Romance", "Romance drama", "United Kingdom", "English", "2024-H1", None, None, 39.0, "Netflix Engagement Report H1 2024"),
    ("Society of the Snow", "Movie", "Drama", "Survival drama", "Spain", "Spanish", "2024-H1", None, None, 104.0, "Netflix Engagement Report H1 2024"),
    ("Berlin (Season 2)", "TV Show", "Crime", "Heist crime drama", "Spain", "Spanish", "2024-H1", None, None, 49.0, "Netflix Engagement Report H1 2024"),
    ("The Asunta Case", "TV Show", "Crime", "Crime drama", "Spain", "Spanish", "2024-H1", None, None, 31.0, "Netflix Engagement Report H1 2024"),
    ("Raising Voices", "TV Show", "Drama", "Drama", "Spain", "Spanish", "2024-H1", None, None, 25.0, "Netflix Engagement Report H1 2024"),
    ("Queen of Tears", "TV Show", "Romance", "Romance drama", "South Korea", "Korean", "2024-H1", None, None, 29.0, "Netflix Engagement Report H1 2024"),
    ("Parasyte: The Grey", "TV Show", "Horror", "Sci-fi horror", "South Korea", "Korean", "2024-H1", None, None, 25.0, "Netflix Engagement Report H1 2024"),
    ("My Demon", "TV Show", "Fantasy", "Fantasy romance", "South Korea", "Korean", "2024-H1", None, None, 18.0, "Netflix Engagement Report H1 2024"),
    ("The Roast of Tom Brady", "Special", "Comedy", "Comedy special", "United States", "English", "2024-H1", None, None, 22.0, "Netflix Engagement Report H1 2024"),
    ("Dave Chappelle: The Dreamer", "Special", "Comedy", "Stand-up comedy", "United States", "English", "2024-H1", None, None, 17.0, "Netflix Engagement Report H1 2024"),
    ("Alpha Males (2 Seasons)", "TV Show", "Comedy", "Comedy", "Spain", "Spanish", "2024-H1", None, None, 14.0, "Netflix Engagement Report H1 2024"),
    ("Young Sheldon (6 Seasons)", "TV Show", "Comedy", "Sitcom (licensed)", "United States", "English", "2024-H1", None, None, 106.0, "Netflix Engagement Report H1 2024"),
    ("Love Is Blind", "TV Show", "Reality", "Reality dating", "United States", "English", "2024-H1", None, None, 21.0, "Netflix Engagement Report H1 2024"),
    ("Perfect Match", "TV Show", "Reality", "Reality dating", "United States", "English", "2024-H1", None, None, 11.0, "Netflix Engagement Report H1 2024"),
    ("Is It Cake?", "TV Show", "Reality", "Reality competition", "United States", "English", "2024-H1", None, None, 9.0, "Netflix Engagement Report H1 2024"),
    ("The Super Mario Bros. Movie", "Movie", "Animation", "Animated adventure (licensed)", "United States", "English", "2024-H1", None, None, 80.0, "Netflix Engagement Report H1 2024"),
    ("Minions", "Movie", "Animation", "Animated comedy (licensed)", "United States", "English", "2024-H1", None, None, 73.0, "Netflix Engagement Report H1 2024"),
    ("The Boss Baby", "Movie", "Animation", "Animated comedy (licensed)", "United States", "English", "2024-H1", None, None, 64.0, "Netflix Engagement Report H1 2024"),
    ("American Nightmare", "TV Show", "Documentary", "True crime documentary", "United States", "English", "2024-H1", None, None, 55.0, "Netflix Engagement Report H1 2024"),
    ("The Greatest Night in Pop", "Movie", "Documentary", "Music documentary", "United States", "English", "2024-H1", None, None, 25.0, "Netflix Engagement Report H1 2024"),
    ("Formula 1: Drive to Survive", "TV Show", "Documentary", "Sports documentary", "United Kingdom", "English", "2024-H1", None, None, 12.0, "Netflix Engagement Report H1 2024"),
    ("America's Sweethearts: Dallas Cowboys Cheerleaders", "TV Show", "Documentary", "Reality documentary", "United States", "English", "2024-H1", None, None, 6.0, "Netflix Engagement Report H1 2024"),
    ("Love on the Spectrum", "TV Show", "Documentary", "Reality documentary", "United States", "English", "2024-H1", None, None, 11.0, "Netflix Engagement Report H1 2024"),

    # ── 2024-H2 (Engagement Report #4, Jul-Dec 2024) ──
    ("Squid Game (Season 2)", "TV Show", "Thriller", "Survival drama", "South Korea", "Korean", "2024-H2", "2024-12-26", None, 87.0, "Netflix Engagement Report H2 2024"),
    ("Dr. Seuss' The Grinch", "Movie", "Animation", "Animated family", "United States", "English", "2024-H2", None, None, 67.0, "Netflix Engagement Report H2 2024"),
    ("Trolls Band Together", "Movie", "Animation", "Animated comedy", "United States", "English", "2024-H2", None, None, 61.0, "Netflix Engagement Report H2 2024"),
    ("That Christmas", "Movie", "Animation", "Animated family", "United Kingdom", "English", "2024-H2", None, None, 60.0, "Netflix Engagement Report H2 2024"),
    ("Sing", "Movie", "Animation", "Animated musical comedy (licensed)", "United States", "English", "2024-H2", None, None, 58.0, "Netflix Engagement Report H2 2024"),
    ("Saving Bikini Bottom: The Sandy Cheeks Movie", "Movie", "Animation", "Animated family", "United States", "English", "2024-H2", None, None, 56.0, "Netflix Engagement Report H2 2024"),
    ("The Menendez Brothers", "TV Show", "Documentary", "True crime documentary", "United States", "English", "2024-H2", None, None, 39.0, "Netflix Engagement Report H2 2024"),
    ("American Murder: Laci Peterson", "TV Show", "Documentary", "True crime documentary", "United States", "English", "2024-H2", None, None, 37.0, "Netflix Engagement Report H2 2024"),
    ("Worst Ex Ever", "TV Show", "Documentary", "True crime documentary", "United States", "English", "2024-H2", None, None, 26.0, "Netflix Engagement Report H2 2024"),
    ("Into the Fire: The Lost Daughter", "TV Show", "Documentary", "True crime documentary", "United States", "English", "2024-H2", None, None, 25.0, "Netflix Engagement Report H2 2024"),
    ("La Palma", "TV Show", "Thriller", "Disaster thriller", "Norway", "Norwegian", "2024-H2", None, None, 52.0, "Netflix Engagement Report H2 2024"),
    ("The Accident", "TV Show", "Drama", "Drama thriller", "Mexico", "Spanish", "2024-H2", None, None, 41.0, "Netflix Engagement Report H2 2024"),
    ("Family Pack", "Movie", "Comedy", "Comedy horror", "France", "French", "2024-H2", None, None, 41.0, "Netflix Engagement Report H2 2024"),
    ("The Empress (Season 2)", "TV Show", "Drama", "Historical drama", "Germany", "German", "2024-H2", None, None, 19.0, "Netflix Engagement Report H2 2024"),
    ("Senna", "TV Show", "Drama", "Biographical drama", "Brazil", "Portuguese", "2024-H2", None, None, 15.0, "Netflix Engagement Report H2 2024"),
    ("One Hundred Years of Solitude", "TV Show", "Drama", "Magical realism drama", "Colombia", "Spanish", "2024-H2", None, None, 9.0, "Netflix Engagement Report H2 2024"),
    ("Tokyo Swindlers", "TV Show", "Crime", "Crime drama", "Japan", "Japanese", "2024-H2", None, None, 12.0, "Netflix Engagement Report H2 2024"),
    ("Drawing Closer", "TV Show", "Romance", "Romance drama", "Japan", "Japanese", "2024-H2", None, None, 8.0, "Netflix Engagement Report H2 2024"),
    ("Jujutsu Kaisen", "TV Show", "Animation", "Anime action fantasy", "Japan", "Japanese", "2024-H2", None, None, 8.0, "Netflix Engagement Report H2 2024"),
    ("Officer Black Belt", "TV Show", "Action", "Action comedy", "South Korea", "Korean", "2024-H2", None, None, 40.0, "Netflix Engagement Report H2 2024"),
    ("Mission: Cross", "Movie", "Action", "Action comedy", "South Korea", "Korean", "2024-H2", None, None, 23.0, "Netflix Engagement Report H2 2024"),
    ("Love Next Door", "TV Show", "Romance", "Romance comedy", "South Korea", "Korean", "2024-H2", None, None, 20.0, "Netflix Engagement Report H2 2024"),
    ("Culinary Class Wars", "TV Show", "Reality", "Reality competition", "South Korea", "Korean", "2024-H2", None, None, 17.0, "Netflix Engagement Report H2 2024"),
    ("Maharaja", "Movie", "Action", "Action thriller", "India", "Tamil", "2024-H2", None, None, 25.0, "Netflix Engagement Report H2 2024"),
    ("Do Patti", "Movie", "Crime", "Crime thriller", "India", "Hindi", "2024-H2", None, None, 20.0, "Netflix Engagement Report H2 2024"),
    ("IC 814: The Kandahar Hijack", "TV Show", "Drama", "Historical drama", "India", "Hindi", "2024-H2", None, None, 12.0, "Netflix Engagement Report H2 2024"),
    ("Black Doves", "TV Show", "Thriller", "Spy thriller", "United Kingdom", "English", "2024-H2", None, None, 38.8, "Netflix Engagement Report H2 2024"),
    ("Outer Banks (Season 4)", "TV Show", "Adventure", "Adventure drama", "United States", "English", "2024-H2", None, 320.0, 35.7, "Netflix Engagement Report H2 2024"),
    ("Cobra Kai (Final Season)", "TV Show", "Action", "Action comedy drama", "United States", "English", "2024-H2", None, None, 38.3, "Netflix Engagement Report H2 2024"),
    ("Prison Break (Season 1)", "TV Show", "Action", "Action thriller (licensed)", "United States", "English", "2024-H2", None, 511.0, 31.9, "Netflix Engagement Report H2 2024"),
    ("The Lincoln Lawyer (Season 3)", "TV Show", "Drama", "Legal drama", "United States", "English", "2024-H2", None, None, 32.5, "Netflix Engagement Report H2 2024"),
    ("Jake Paul vs. Mike Tyson", "Live Event", "Sports", "Boxing event", "United States", "English", "2024-H2", None, None, 48.9, "Netflix Engagement Report H2 2024"),

    # ── 2025-H1 (Engagement Report #5, Jan-Jun 2025) ──
    ("Back in Action", "Movie", "Action", "Action comedy", "United States", "English", "2025-H1", "2025-01-17", None, 147.2, "Netflix Engagement Report H1 2025"),
    ("Adolescence", "TV Show", "Drama", "Coming-of-age drama (limited series)", "United Kingdom", "English", "2025-H1", None, None, 142.6, "Netflix Engagement Report H1 2025"),
    ("Squid Game (Seasons 1-3 combined)", "TV Show", "Thriller", "Survival drama", "South Korea", "Korean", "2025-H1", "2025-06-27", None, 231.0, "Netflix Engagement Report H1 2025"),
    ("KPop Demon Hunters", "Movie", "Animation", "Musical fantasy action (partial period)", "United States", "English", "2025-H1", "2025-06-20", None, 37.0, "Netflix Engagement Report H1 2025"),
    ("Ms. Rachel (Season 1)", "TV Show", "Family", "Kids education", "United States", "English", "2025-H1", None, None, 53.0, "Netflix Engagement Report H1 2025"),
    ("Asterix & Obelix: The Big Fight", "Movie", "Animation", "Animated comedy", "France", "French", "2025-H1", None, None, 16.0, "Netflix Engagement Report H1 2025"),
    ("Gabby's Dollhouse (All Seasons)", "TV Show", "Family", "Kids animation", "United States", "English", "2025-H1", None, None, 108.0, "Netflix Engagement Report H1 2025"),
    ("When Life Gives You Tangerines", "TV Show", "Romance", "Romance drama", "South Korea", "Korean", "2025-H1", None, None, 35.0, "Netflix Engagement Report H1 2025"),
    ("The Trauma Code: Heroes on Call (Season 1)", "TV Show", "Drama", "Medical drama", "South Korea", "Korean", "2025-H1", None, None, 34.0, "Netflix Engagement Report H1 2025"),
    ("Weak Hero: Class 1", "TV Show", "Action", "Action drama", "South Korea", "Korean", "2025-H1", None, None, 22.0, "Netflix Engagement Report H1 2025"),
    ("Weak Hero: Class 2", "TV Show", "Action", "Action drama", "South Korea", "Korean", "2025-H1", None, None, 20.0, "Netflix Engagement Report H1 2025"),
    ("Secrets We Keep", "TV Show", "Drama", "Psychological drama", "Denmark", "Danish", "2025-H1", None, None, 34.0, "Netflix Engagement Report H1 2025"),
    ("Number 24", "Movie", "Drama", "War drama", "Norway", "Norwegian", "2025-H1", None, None, 24.0, "Netflix Engagement Report H1 2025"),
    ("The Are Murders (Season 1)", "TV Show", "Crime", "Crime drama", "Sweden", "Swedish", "2025-H1", None, None, 33.0, "Netflix Engagement Report H1 2025"),
    ("The Breakthrough", "Movie", "Crime", "Crime drama", "Sweden", "Swedish", "2025-H1", None, None, 29.0, "Netflix Engagement Report H1 2025"),
    ("The Glass Dome", "TV Show", "Thriller", "Psychological thriller", "Sweden", "Swedish", "2025-H1", None, None, 20.0, "Netflix Engagement Report H1 2025"),
    ("Medusa (Season 1)", "TV Show", "Crime", "Crime drama", "Colombia", "Spanish", "2025-H1", None, None, 21.0, "Netflix Engagement Report H1 2025"),
    ("Fake Profile: Killer Match", "Movie", "Crime", "Crime thriller", "Colombia", "Spanish", "2025-H1", None, None, 20.0, "Netflix Engagement Report H1 2025"),
    ("Karol G: Tomorrow Was Beautiful", "Special", "Documentary", "Concert documentary", "Colombia", "Spanish", "2025-H1", None, None, 13.0, "Netflix Engagement Report H1 2025"),
    ("Orange Is the New Black", "TV Show", "Comedy", "Comedy drama (legacy title)", "United States", "English", "2025-H1", None, 100.0, None, "Netflix Engagement Report H1 2025"),
    ("Ozark", "TV Show", "Crime", "Crime drama (legacy title)", "United States", "English", "2025-H1", None, 100.0, None, "Netflix Engagement Report H1 2025"),
    ("Money Heist", "TV Show", "Crime", "Heist crime drama (legacy title)", "Spain", "Spanish", "2025-H1", None, 100.0, None, "Netflix Engagement Report H1 2025"),
    ("Zero Day", "TV Show", "Thriller", "Political thriller", "United States", "English", "2025-H1", None, None, 61.0, "Netflix Engagement Report H1 2025"),
    ("Running Point", "TV Show", "Comedy", "Comedy", "United States", "English", "2025-H1", None, None, 41.0, "Netflix Engagement Report H1 2025"),
    ("WWE Raw (Weekly, combined)", "Live Event", "Sports", "Wrestling (26 episodes combined)", "United States", "English", "2025-H1", None, None, 88.6, "Netflix Engagement Report H1 2025"),
    ("WWE SmackDown (Weekly, combined)", "Live Event", "Sports", "Wrestling (25 episodes combined)", "United States", "English", "2025-H1", None, None, 21.1, "Netflix Engagement Report H1 2025"),

    # ── 2025-H2 (Engagement Report #6, Jul-Dec 2025) ──
    ("KPop Demon Hunters", "Movie", "Animation", "Musical fantasy action", "United States", "English", "2025-H2", "2025-06-20", None, 482.0, "Netflix Engagement Report H2 2025"),
    ("KPop Demon Hunters: Lyric Videos", "Special", "Music", "Musical lyric videos", "United States", "English", "2025-H2", None, None, 32.0, "Netflix Engagement Report H2 2025"),
    ("Wednesday (Season 2)", "TV Show", "Comedy", "Supernatural mystery comedy", "United States", "English", "2025-H2", "2025-08-06", None, 124.0, "Netflix Engagement Report H2 2025"),
    ("Stranger Things (Season 5)", "TV Show", "Science Fiction", "Sci-fi horror", "United States", "English", "2025-H2", "2025-11-26", None, 94.0, "Netflix Engagement Report H2 2025"),
    ("Stranger Things (All 5 Seasons combined)", "TV Show", "Science Fiction", "Sci-fi horror", "United States", "English", "2025-H2", None, None, 275.0, "Netflix Engagement Report H2 2025"),
    ("Wednesday (Season 1)", "TV Show", "Comedy", "Supernatural mystery comedy (renewed interest)", "United States", "English", "2025-H2", None, None, 47.0, "Netflix Engagement Report H2 2025"),
    ("Gabby's Dollhouse (All Seasons)", "TV Show", "Family", "Kids animation", "United States", "English", "2025-H2", None, None, 108.0, "Netflix Engagement Report H2 2025"),
    ("Peppa Pig", "TV Show", "Family", "Kids animation", "United Kingdom", "English", "2025-H2", None, None, 90.0, "Netflix Engagement Report H2 2025"),
    ("Ms. Rachel", "TV Show", "Family", "Kids education", "United States", "English", "2025-H2", None, None, 73.0, "Netflix Engagement Report H2 2025"),
    ("In Your Dreams", "Movie", "Animation", "Animated family", "United States", "English", "2025-H2", None, None, 47.0, "Netflix Engagement Report H2 2025"),
    ("Mark Rober's CrunchLabs (Season 1)", "TV Show", "Family", "Kids education", "United States", "English", "2025-H2", None, None, 12.0, "Netflix Engagement Report H2 2025"),
    ("Sesame Street: Volume 1", "TV Show", "Family", "Kids education", "United States", "English", "2025-H2", None, None, 6.0, "Netflix Engagement Report H2 2025"),
    ("Last Samurai Standing (Season 1)", "TV Show", "Action", "Action drama", "Japan", "Japanese", "2025-H2", None, None, 21.0, "Netflix Engagement Report H2 2025"),
    ("Alice in Borderland (Season 3)", "TV Show", "Science Fiction", "Survival thriller", "Japan", "Japanese", "2025-H2", None, None, 25.0, "Netflix Engagement Report H2 2025"),
    ("The Elixir", "TV Show", "Fantasy", "Fantasy drama", "Indonesia", "Indonesian", "2025-H2", None, None, 23.0, "Netflix Engagement Report H2 2025"),
    ("The Bads of Bollywood (Season 1)", "TV Show", "Comedy", "Comedy drama", "India", "Hindi", "2025-H2", None, None, 10.0, "Netflix Engagement Report H2 2025"),
    ("The Asset (Season 1)", "TV Show", "Drama", "Drama", "Denmark", "Danish", "2025-H2", None, None, 23.0, "Netflix Engagement Report H2 2025"),
    ("Mango", "TV Show", "Drama", "Drama", "Denmark", "Danish", "2025-H2", None, None, 21.0, "Netflix Engagement Report H2 2025"),
    ("Troll 2", "Movie", "Action", "Monster action adventure", "Norway", "Norwegian", "2025-H2", None, None, 44.0, "Netflix Engagement Report H2 2025"),
    ("Angela", "TV Show", "Drama", "Drama", "Mexico", "Spanish", "2025-H2", None, None, 36.0, "Netflix Engagement Report H2 2025"),
    ("Billionaires' Bunker", "TV Show", "Drama", "Drama", "Spain", "Spanish", "2025-H2", None, None, 28.0, "Netflix Engagement Report H2 2025"),
    ("Two Graves", "TV Show", "Crime", "Crime drama", "Spain", "Spanish", "2025-H2", None, None, 26.0, "Netflix Engagement Report H2 2025"),
    ("Old Dog, New Tricks (Season 1)", "TV Show", "Comedy", "Comedy drama", "Mexico", "Spanish", "2025-H2", None, None, 15.0, "Netflix Engagement Report H2 2025"),
    ("French Lover", "Movie", "Comedy", "Romantic comedy", "France", "French", "2025-H2", None, None, 33.0, "Netflix Engagement Report H2 2025"),
    ("Abandoned Man", "Movie", "Drama", "Drama", "France", "French", "2025-H2", None, None, 28.0, "Netflix Engagement Report H2 2025"),
    ("Old Money (Season 1)", "TV Show", "Drama", "Drama", "Turkey", "Turkish", "2025-H2", None, None, 17.0, "Netflix Engagement Report H2 2025"),
    ("WWE Live Events (combined)", "Live Event", "Sports", "Wrestling (combined viewing hours)", "United States", "English", "2025-H2", None, 280.0, None, "Netflix Engagement Report H2 2025"),
]

COLUMNS = [
    "title", "content_type", "primary_genre", "genre_detail", "country_origin",
    "language", "report_period", "premiere_date", "hours_viewed_millions",
    "views_millions", "source",
]

if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(__file__), "netflix_engagement_report.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in ROWS:
            w.writerow(["" if v is None else v for v in r])
    print(f"Wrote {len(ROWS)} rows -> {out_path}")
