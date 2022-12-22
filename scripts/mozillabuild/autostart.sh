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

if [ "$BUILDSM" == "--enable-address-sanitizer" ] ; then
    # For future MSVCs, see where the build process complains about the lack of a .pdb at a new desired destination
    echo "Copying over clang_rt.asan_dynamic-x86_64.pdb ..." ;
    # MSVC 2019:
    cp "$HOME"/.mozbuild/clang/lib/clang/"$(ls "$HOME"/.mozbuild/clang/lib/clang/)"/lib/windows/clang_rt.asan_dynamic-x86_64.pdb \
      /c/Program\ Files\ \(x86\)/Microsoft\ Visual\ Studio/2019/Enterprise/VC/Tools/MSVC/14.29.30133/bin/HostX64/x64/
    # MSVC 2022:
    #   /c/Program\ Files/Microsoft\ Visual\ Studio/2022/Enterprise/VC/Tools/MSVC/14.34.31933/bin/HostX64/x64/

    # Patch m-c bug 1802675
    sed -i 's/if CONFIG\["OS_TARGET"\] == "WINNT":/if CONFIG["MOZ_MEMORY"] and CONFIG["OS_TARGET"] == "WINNT":/' ~/trees/mozilla-central/memory/mozalloc/moz.build ;
    hg -R ~/trees/mozilla-central/ diff ;
fi ;

echo "=== pytest attempt: 1 ===" ;
if ! BUILDSM="$*" python -u -m pytest --bandit --black --cov --flake8 --mypy --pylint ; then
    echo "=== pytest attempt: 2 ===" ;
    echo "=== Removing shell-cache ... ===" ;
    rm -rf "$HOME"/shell-cache/ ;
    echo "=== Removed shell-cache successfully! ===" ;
    if ! BUILDSM="$*" python -u -m pytest --bandit --black --cov --flake8 --mypy --pylint ; then
        echo "=== pytest attempt: 3 ===" ;
        echo "=== Removing shell-cache ... ===" ;
        rm -rf "$HOME"/shell-cache/ ;
        echo "=== Removed shell-cache successfully! ===" ;
        if ! BUILDSM="$*" python -u -m pytest --bandit --black --cov --flake8 --mypy --pylint ; then
            date > "$HOME"/pytest-failure.txt ;
        fi ;
    fi ;
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
