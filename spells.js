$.fn.dataTable.ext.search.push(
    function (settings, data, dataIndex) {
        var filterValue = $('#spellLevelFilter').val(); // Get the value of the dropdown
        var spellLevelColumn = data[2]; // Assuming level data is in the third column

        // If no filter is selected, do not filter the rows
        if (!filterValue) {
            return true;
        }

        // Parse the spell level column for 'sorcerer/wizard X' where X is the level
        var levelMatch = spellLevelColumn.match(/sorcerer\/wizard (\d+)/);

        // If there's a match and it equals the filter value, return true; otherwise, false
        if (levelMatch && levelMatch[1] === filterValue) {
            return true;
        }
        return false;
    }
);

$(document).ready(function () {
    let dataTable = null;

    // Load the TSV data using jQuery's AJAX
    $.ajax({
        url: 'spells.tsv', // Make sure the file name matches the uploaded TSV file
        dataType: 'text',
    }).done(successFunction);

    function successFunction(data) {
        // Split the data into rows
        let allRows = data.split(/\r?\n|\r/);
        let headers = allRows[0].split(/\t/); // Extract headers to find column indices
        let tableData = [];

        // Process each row
        for (let singleRow = 1; singleRow < allRows.length; singleRow++) {
            let rowCells = allRows[singleRow].split(/\t/);

            // Extract data based on indices provided in the sample
            let name = rowCells[1];
            let school = rowCells[2];
            let level = rowCells[headers.indexOf('spell_level')];
            let castingTime = rowCells[headers.indexOf('casting_time')];
            let range = rowCells[headers.indexOf('range')];
            // Link logic
            let link = rowCells[headers.indexOf('link')];
            if (!link || link.trim().toLowerCase() === 'null' || link.trim() === name) {
                let spellNameFormatted = name.toLowerCase().replace(/\s+/g, '-').replace(/[’'"]/g, '');
                let firstLetter = spellNameFormatted.charAt(0);
                link = `https://www.d20pfsrd.com/magic/all-spells/${firstLetter}/${spellNameFormatted}`;
            }
            let onMyList = rowCells[headers.indexOf('On my list')];
            // Extract and refactor level data
            let levelCell = rowCells[headers.indexOf('spell_level')];
            let levelMatches = levelCell.match(/sorcerer\/wizard (\d+)/);
            let wizardLevel = levelMatches ? levelMatches[0] : ''; // Extract "sorcerer/wizard X" where X is the level

            // Push the extracted data into the tableData array
            tableData.push({
                "name": name,
                "school": school,
                "level": level,
                "casting_time": castingTime,
                "range": range,
                "hyperlink": link, // Link is now added
                "on_my_list": onMyList
            });
        }

        // Initialize DataTable with the parsed data
        // Initialize DataTable with the parsed data
        dataTable = $('#spellsTable').DataTable({
            data: tableData,
            pageLength: 100,
            columns: [
                {
                    title: 'Name',
                    data: 'name',
                    render: function (data, type, row) {
                        return '<a href="' + row.hyperlink + '" target="_blank">' + data + '</a>';
                    }
                },
                { title: 'School', data: 'school' },
                {
                    title: 'Level',
                    data: 'level',
                    render: function (data, type, row) {
                        // Check the type of action DataTables is currently performing
                        if (type === 'display') {
                            // If it's for display, show only the level number for sorcerer/wizard
                            var levelMatch = data.match(/sorcerer\/wizard (\d+)/);
                            return levelMatch ? levelMatch[1] : ''; // Return just the level number
                        } else {
                            // For other types (like sorting or filtering), return the full data
                            return data;
                        }
                    }
                },
                { title: 'Casting Time', data: 'casting_time' },
                { title: 'Range', data: 'range' },
                { title: 'On my list', data: 'on_my_list', visible: false }
            ]
        });
        // Event listener for the dropdown
        $('#spellLevelFilter').on('change', function () {
            dataTable.draw(); // Redraw the table with the new filter applied
        });

    }




    // Event listener for the checkbox
    $('#myListFilter').on('change', function () {
        // Filter the dataTable based on the "On my list" column
        dataTable.column(5).search(this.checked ? '1' : '', true, false).draw();
    });

    // $('#spellLevelFilter').on('change', function () {
    //     if (dataTable) {
    //         // Assume the 'Level' column is the third one (index 2, since indexing starts at 0)
    //         let levelIndex = 2; // This should match the actual index of the 'Level' column in your DataTable
    //         let searchTerm = this.value ? this.value : '';
    //         dataTable.column(levelIndex).search(searchTerm).draw();
    //     }
    // });



});