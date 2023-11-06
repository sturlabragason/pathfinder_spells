# Pathfinder Spells

A web-based tool tailored for Pathfinder spellcasters, designed to manage and filter spells for a single character. The project allows users to filter spells by level and whether they are included in the user's personalized list.

## Features

- **Spell Filtering**: Users can filter spells by level using a dropdown menu.
- **Custom Spell List**: Users can mark spells to be included in their personal spell list for quick access.
- **Responsive Design**: The website is styled with Tailwind CSS and custom styles for a parchment-like aesthetic.
- **Interactive Tables**: Spells are displayed in an interactive table powered by DataTables for easy sorting and filtering.

## Caveats

- The spell data is currently tailored to a single character's spell list. Users looking to manage spells for multiple characters will need to modify the data source.
- The website is designed for desktop use, and while it is responsive, the experience on mobile devices may vary.

## Customization

- Spells are stored in a TSV (Tab-Separated Values) file, which can be edited to reflect the spells available to a specific character.
- Custom spell levels can be set to match the character's progression.
- The JavaScript file (`spells.js`) can be modified to change filtering logic or adapt to different spell data structures.

## Note on Link Creation Logic

The JavaScript code includes a quick workaround for creating links to spell descriptions. This logic is not exhaustive and does not guarantee functional links for all spells but serves the current purpose for a large number of them. For a full implementation, additional logic or a complete dataset with valid URLs would be required.

## Usage with Docker

To set up and run the Pathfinder Spells application:

1. Clone the repository or download the files to your local machine.
2. Optionally, edit the `spells.tsv` file to include your character's spells and desired metadata.
3. In the directory with your project files, run the following command:
```bash
docker build -t pathfinder-spells . && docker run -d -p 80:80 pathfinder-spells
```
4. After running the command, browse to http://localhost in your web browser to access the application.

## Data Source

The spell data used in this project is sourced from a publicly available Google Spreadsheet maintained by Kyler Dixon, which can be found here:

- [Pathfinder Spell Database](https://docs.google.com/spreadsheets/d/197aOpt71IDoO6yCmOB1mtEhGE598jBVs5iZox8YMHAk/edit?usp=sharing)

## Open Game License

This project presents spell data and information under the Open Game License (OGL) as provided by Paizo Publishing for the Pathfinder Roleplaying Game. Users of this project should ensure they comply with the OGL when using and distributing content related to Pathfinder.

## Links

- Repository: [Pathfinder Spells on GitHub](https://github.com/sturlabragason/pathfinder_spells)
- Published Website: [Pathfinder Spells Website](https://sturlabragason.github.io/spells/)

For any questions or issues, please open an issue on the GitHub repository.

