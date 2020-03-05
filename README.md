# dulsort
Command-line tool to identify large-sized directories quickly

<img src="dulsort-demo.gif" data-canonical-src="https://github.com/ovikholt/dulsort/blob/master/dulsort-demo.gif" width="480">

You could also just do

    du -sch .* * 2>/dev/null | sort --human-numeric-sort

though... but it's not as fun, and you don't get the pretty colors. Also, `dulsort` uses cache, so it's faster on subsequent runs, while `du` is not.

Note, that a directory *might* change after it's been cached by dulsort and `dulsort` won't realize. If you suspect a size is wrong, do a touch of the directory/file or just of everything in your folder, before running `dulsort` again.

    touch *
    dulsort
