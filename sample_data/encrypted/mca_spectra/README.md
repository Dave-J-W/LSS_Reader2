# Encrypted private MCA spectra (for the cloud session extending the scatter study)

These are the owner's private MCA spectra, cropped and anonymised, encrypted with AES-256 by the local
data agent at the owner's request (2026-11-25). **The key is not in this repository, nor on any issue
or pull request.** The owner puts it into the cloud session's environment as the variable `MCA_KEY`.
Without it, the files cannot be read.

This branch (`claude/local-data-mca-encrypted`) is a transfer only. **Do not merge it into main**: the
parts are about 141 MB.

## Decrypt

From the repository root, on any branch. The steps read the parts from the fetched branch without
checking them out:

    git fetch origin claude/local-data-mca-encrypted
    B=origin/claude/local-data-mca-encrypted; P=sample_data/encrypted/mca_spectra
    T=$(mktemp -d)
    for i in 1 2 3 4; do git show "$B:$P/mca_spectra.tar.xz.enc.part$i" > "$T/mca_spectra.tar.xz.enc.part$i"; done
    git show "$B:$P/SHA256SUMS" > "$T/SHA256SUMS"
    cat "$T"/mca_spectra.tar.xz.enc.part[1-4] > "$T/mca_spectra.tar.xz.enc"
    (cd "$T" && sha256sum -c SHA256SUMS)              # every line must say OK
    mkdir -p sample_data/private/mca_scatter_cloud
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 \
        -in "$T/mca_spectra.tar.xz.enc" -pass env:MCA_KEY \
        | tar -xJ -C sample_data/private/mca_scatter_cloud
    rm -rf "$T"
    ls sample_data/private/mca_scatter_cloud/mca_spectra   # README_HANDOFF.md, load.py, counts.npy, ...

This needs OpenSSL 1.1.1 or later, for `-pbkdf2`. A wrong or missing key stops at `bad decrypt`. The
decrypted folder is under the git-ignored `sample_data/private/`. Start with `mca_spectra/README_HANDOFF.md` there: it lists the format, a loader,
which spectra the study found of interest, and the privacy rules. In short, nothing decrypted is ever
committed. Derived numbers in docs are fine. Spectra, peak positions and images are not.
