# Anonymous review release

Anonymous GitHub can mask repository identifiers and configured terms for the
review copy: https://anonymous.4open.science/. Its upstream usage documentation is
https://github.com/tdurieux/anonymous_github#readme.

Use the service for author/institution masking; do not use it as a secret store or
as the only defense for patient data. Current notebooks must have empty outputs
and no execution/widget state. Individual-content screenshots have been withheld
from the public tree; replacements must use explicitly synthetic narratives.
The original screenshots remain private local material, outside Git/build context.

Configure masking for author names, usernames, email addresses, institution names
and abbreviations, repository owner/URLs, identifying home paths, and old cloud
identifiers. Inspect `NOTICE` specifically: the source retains its required
attribution. `SECURITY.md` directs readers to Git author metadata, which also needs
to remain outside the anonymous artifact. Never add the real masking-term list to
this public repo; maintain it in the service/private notes.

Select a fixed reviewed revision where possible. Inspect both the browser view
and downloaded archive after updating the service: verify masked text, notebook
source, figures, file names, notices and outbound links. Text masking cannot
remove identifying pixels or reliably de-identify detailed narrative prose.

HEAD cleanup does not erase earlier commits or third-party caches. Use a review
snapshot that excludes `.git` and does not expose original commit metadata. If the
service exposes an older file revision, raw/download link or archive, check it
explicitly. Gitleaks still scans full local history for credentials; author masking
is a separate step. Historical data or secret removal from the upstream repository
requires a separate, coordinated history-cleanup decision; these changes do not
rewrite history or claim that previous public copies have disappeared.
