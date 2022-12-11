#! /bin/bash

which python ;
python --version ;
export BUILDSM="$*" ;
echo "BUILDSM env variable is: $BUILDSM" ;
python -u -m pip install --upgrade pip setuptools wheel ;
pushd /d/a/ocs/ocs/ || exit ;

openssl enc -base64 -d <<< SG9zdCAqCkFkZEtleXNUb0FnZW50IHllcwpTdHJpY3RIb3N0S2V5Q2hlY2tpbmcgbm8KCkhvc3QgenpiYXNlLmdpdGh1Yi5jb20KSG9zdE5hbWUgZ2l0aHViLmNvbQpVc2VyIGdpdApJZGVudGl0eUZpbGUgfi8uc3NoL2lkX2VkMjU1MTlfUk9fenpiYXNlCklkZW50aXRpZXNPbmx5IHllcwo= > "$HOME"/.ssh/config ;
python -u -m pip install -r requirements.txt ;
python -u -m pip install --upgrade -e . ;

# Run mach bootstrap
pushd "$HOME"/trees/mozilla-central/ || exit ;
# No to mercurial changes, pushing commits upstream and telemetry submission
./mach bootstrap --app=js << EOF

n

n

n

EOF
popd || exit ;

if ! BUILDSM="$*" python -u -m pytest --bandit --black --cov --flake8 --mypy --pylint ; then
    date > "$HOME"/pytest-failure.txt ;
fi ;
unset BUILDSM
popd || exit ;

# Create a tarball and SHA-256 checksum only if pytest ran without any errors
if [ ! -f "$HOME"/pytest-failure.txt ]; then
    pushd "$HOME"/shell-cache || exit ;
    for f in * ;
    do
        [[ $f =~ "js-" ]] && time tar -cpf - "$f" | zstd -T0 --long -19 > "$f".tar.zst ;
        shasum -a 256 -b "$f".tar.zst | tee "$f".tar.zst.sha256 ;
    done ;
    popd || exit ;
fi
