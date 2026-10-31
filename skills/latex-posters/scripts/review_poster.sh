#!/bin/bash
# Read-only Poppler preflight. Exit 0: automated checks passed; 1: failure;
# 2: incomplete because a required inspector is missing. Visual review is always required.
export LC_ALL=C

usage() { printf 'Usage: %s <poster.pdf>\n' "$0"; }
if [ "${1:-}" = '--help' ] || [ "${1:-}" = '-h' ]; then usage; exit 0; fi
if [ "$#" -ne 1 ]; then usage; exit 1; fi
POSTER_FILE=$1
# A leading dash must not become an inspector option.
case "$POSTER_FILE" in /*) ;; *) POSTER_FILE="./$POSTER_FILE" ;; esac
if [ ! -f "$POSTER_FILE" ]; then
    printf '[FAIL] File not found: %s\n' "$POSTER_FILE"
    exit 1
fi
failed=0
incomplete=0
command_exists() { command -v "$1" >/dev/null 2>&1; }
missing() { printf '[WARN] %s not installed; check incomplete. Install Poppler.\n' "$1"; incomplete=1; }

printf 'Poster PDF Quality Check\nFile: %s\n\n' "$POSTER_FILE"
printf '[1] Page Dimensions:\n'
PDF_INFO=''
if command_exists pdfinfo; then
    if PDF_INFO=$(pdfinfo "$POSTER_FILE" 2>&1); then
        printf '%s\n' "$PDF_INFO" | awk '/^Page size:/ {print; found=1} END {if (!found) exit 1}' || failed=1
        printf '%s\n' "$PDF_INFO" | awk '
            function near(a,b) {return (a-b < 2 && b-a < 2)}
            /^Page size:/ {
                w=$3; h=$5
                if (near(w,2383.94) && near(h,3370.39)) label="A0 Portrait"
                else if (near(w,3370.39) && near(h,2383.94)) label="A0 Landscape"
                else if (near(w,1683.78) && near(h,2383.94)) label="A1 Portrait"
                else if (near(w,2383.94) && near(h,1683.78)) label="A1 Landscape"
                else if (near(w,2592) && near(h,3456)) label="36 x 48 inches Portrait"
                else if (near(w,3456) && near(h,2592)) label="36 x 48 inches Landscape"
                else label="Custom dimensions"
                print "[INFO] " label "; compare exact dimensions with venue requirements."
            }'
    else
        printf '[FAIL] pdfinfo could not read the PDF.\n%s\n' "$PDF_INFO"
        PDF_INFO=''
        failed=1
    fi
else
    missing pdfinfo
fi

printf '\n[2] Page Count:\n'
if [ -n "$PDF_INFO" ]; then
    PAGE_COUNT=$(printf '%s\n' "$PDF_INFO" | awk '/^Pages:/ {print $2}')
    if [ "$PAGE_COUNT" = 1 ]; then
        printf '[OK] Single page.\n'
    else
        printf '[FAIL] Expected one page; found: %s\n' "${PAGE_COUNT:-unknown}"
        failed=1
    fi
else
    printf '[WARN] Page count unavailable.\n'
fi

printf '\n[3] File Size:\n'
FILE_SIZE_BYTES=$(wc -c < "$POSTER_FILE")
printf '%s bytes. File size alone does not establish image quality.\n' "$FILE_SIZE_BYTES"
if [ "$FILE_SIZE_BYTES" -gt 52428800 ]; then
    printf '[WARN] Over 50 MiB; check the submission limit before creating a separate compressed copy.\n'
fi

printf '\n[4] Font Embedding:\n'
if command_exists pdffonts; then
    if FONT_OUTPUT=$(pdffonts "$POSTER_FILE" 2>&1); then
        printf '%s\n' "$FONT_OUTPUT"
        # Font type names contain spaces. The five rightmost fields are stable:
        # emb, sub, uni, object number, generation. Inspect ALL rows.
        if ! printf '%s\n' "$FONT_OUTPUT" | awk '
            NR==1 {if ($0 !~ /emb.*sub.*uni.*object ID/) invalid=1; next}
            NR>2 && NF {
                count++
                if (NF<8 || ($(NF-4)!="yes" && $(NF-4)!="no")) invalid=1
                else if ($(NF-4)=="no") bad++
            }
            END {
                if (invalid || NR<2) {print "[FAIL] Unrecognized pdffonts output."; exit 1}
                if (bad) {print "[FAIL] " bad " font(s) are NOT embedded."; exit 1}
                if (count) print "[OK] All " count " listed fonts are embedded."
                else print "[INFO] No PDF fonts listed; check for outlined or rasterized text."
            }'; then
            printf 'Rebuild the LaTeX or imported figure source with embeddable fonts.\n'
            failed=1
        fi
    else
        printf '[FAIL] pdffonts failed.\n%s\n' "$FONT_OUTPUT"
        failed=1
    fi
else
    missing pdffonts
fi

printf '\n[5] Image Quality:\n'
if command_exists pdfimages; then
    if IMAGE_OUTPUT=$(pdfimages -list "$POSTER_FILE" 2>&1); then
        printf '%s\n' "$IMAGE_OUTPUT"
        if ! printf '%s\n' "$IMAGE_OUTPUT" | awk '
            NR==1 {if ($0 !~ /x-ppi.*y-ppi/) invalid=1; next}
            NR>2 && NF {
                if (NF<16 || $13 !~ /^[0-9.]+$/ || $14 !~ /^[0-9.]+$/) invalid=1
                if ($3=="image") {count++; if ($13+0<300 || $14+0<300) low++}
            }
            END {
                if (invalid || NR<2) {print "[FAIL] Unrecognized pdfimages output."; exit 1}
                if (!count) print "[INFO] No raster images listed; vector artwork has no raster PPI."
                else if (low) print "[WARN] " low " raster image(s) below 300 PPI at placed size; confirm print needs."
                else print "[OK] Listed raster images are at least 300 PPI at placed size."
            }'; then
            failed=1
        fi
    else
        printf '[FAIL] pdfimages failed.\n%s\n' "$IMAGE_OUTPUT"
        failed=1
    fi
else
    missing pdfimages
fi

printf '\n[6] Manual Visual Inspection Required:\n'
printf '%s\n' \
    '  [ ] No clipping or overlap at any edge, column, title, or footer.' \
    '  [ ] Readable typography and figure labels at the intended viewing distance.' \
    '  [ ] Correct data, units, uncertainty, citations, authors, and affiliations.' \
    '  [ ] No draft placeholders; all figure captions and legends are accurate.' \
    '  [ ] Suitable contrast; categories use labels or shapes as well as color.' \
    '  [ ] QR codes scan and lead to the intended public resource.'
printf '\n[7] Recommended Next Steps:\n'
printf '%s\n' \
    '  - Inspect a rendered PDF and its LaTeX log; automated checks do not detect all overflow.' \
    '  - A0 to A4 is approximately 25% linear scale; 36 x 48 inches needs 9 x 12 inches at 25%.' \
    '  - View a reduced proof at the same scale factor times the full-size viewing distance.' \
    '  - Confirm exact dimensions, color profile, bleed, and any PDF/X requirement with the printer.' \
    '  - Use assets/poster_quality_checklist.md for the remaining checks.'
printf '\nQuality Check Complete\n'
if [ "$failed" -ne 0 ]; then printf '[FAIL] Automated checks found errors.\n'; exit 1; fi
if [ "$incomplete" -ne 0 ]; then printf '[WARN] Automated preflight incomplete.\n'; exit 2; fi
printf '[OK] Automated checks passed; manual visual and scientific review still required.\n'
exit 0
