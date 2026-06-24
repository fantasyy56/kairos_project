#!/usr/bin/env perl
# latexmk configuration for Overleaf
$pdf_mode = 4;  # Use xelatex for Chinese support
$postscript_mode = 0;
$dvi_mode = 0;

# Use xelatex
$xelatex = 'xelatex -interaction=nonstopmode -file-line-error %O %S';

# BibTeX configuration
$bibtex = 'bibtex %O %B';
$biber = 'biber --output_safechars %O %S';

# Use bibtex for .bib files
$bibtex_use = 1;

# Ensure references are found
push @BIBINPUTS, '.';

# Generate PDF
$pdf_mode = 4;
