# Download AGU sessions as notes for Obsidian

Given one or more URLs, makes a set of Markdown files for use in Obsidian. E.g.:

<img width="978" alt="Example note or an AGU session." src="https://user-images.githubusercontent.com/10454527/207506110-68ac370a-a30f-4150-9c0c-0f06484761ae.png">


## Binary vs. Python script

I provide a pre-compiled, packaged Python binary that I have tested on my Apple Silicon Mac. It should work on other Apple Silicon Macs. Call it from a terminal like so (replacing the URL with your URL of interest):
```shell
$ ./agu-notes-from-url https://agu.confex.com/agu/agu24/meetingapp.cgi/Session/233359
```
(If you get a permissions error, try doing `chmod +x agu-notes-from-url` and try again. You should only have to do that once.)

You can also import from a .ics file, which the AGU scheduling webapp allows you to export your personal schedule as:
```shell
$ ./agu-notes-from-url schedule-AGU25.ics
```

If you have some other kind of machine, you'll need to run the script using Python. E.g.:
```shell
$ python3 agu-notes-from-url.py https://agu.confex.com/agu/agu24/meetingapp.cgi/Session/233359
```
More details on the latter below.

## Instructions

### General options:

By default, this program:
- Downloads notes to the directory where it's called
- Includes `#AGUyyyy` but with `yyyy` being the current year
- Does not overwrite existing folders or notes

If you'd like to change any of those, then in the directory where you'll be calling the binary/script (this does not have to be the directory where the binary/script is located, nor does it have to be the directory where you want the notes saved), make a text file called `settings.ini`. Change settings like so:

```ini
[optional]
output_location = /path/to/where/you/want/files/downloaded
overwrite = true
year = 2024
```

If you're importing a .ics file, you can also specify a single date to extract events from:

```ini
[optional]
date = 2025-12-15
```

You can also add `debug = True` to enable verbose printout useful for debugging.

### If not using the binary
Running the script with Python requires that your Python have the following non-standard modules installed:
- `selenium` v4.11 or later
- `icalendar` (if reading a .ics file)

If you get a `ModuleNotFoundError` for either of those, you can install them like so:
```shell
python3 -m pip install icalendar
```
