#! /bin/bash

which python ;
python --version ;
export BUILDSM="$*" ;
echo "BUILDSM env variable is: $BUILDSM" ;

python -u -m pip install --break-system-packages --upgrade pip setuptools wheel uv ;
pushd /d/a/ocs/ocs/ || exit ;

openssl enc -base64 -d <<< SG9zdCAqCkFkZEtleXNUb0FnZW50IHllcwpTdHJpY3RIb3N0S2V5Q2hlY2tpbmcgbm8KCkhvc3QgY3Jhc2gyY292LmdpdGh1Yi5jb20KSG9zdE5hbWUgZ2l0aHViLmNvbQpVc2VyIGdpdApJZGVudGl0eUZpbGUgfi8uc3NoL2lkX2VkMjU1MTlfUk9fY3Jhc2gyY292CklkZW50aXRpZXNPbmx5IHllcwoKSG9zdCB6emJhc2UuZ2l0aHViLmNvbQpIb3N0TmFtZSBnaXRodWIuY29tClVzZXIgZ2l0CklkZW50aXR5RmlsZSB+Ly5zc2gvaWRfZWQyNTUxOV9ST196emJhc2UKSWRlbnRpdGllc09ubHkgeWVzCg== > "$HOME"/.ssh/config ;
python -u -m uv pip install --break-system-packages -r requirements.txt ;
python -u -m uv pip install --break-system-packages --upgrade -e . ;

# Run mach bootstrap
pushd "$HOME"/trees/firefox/ || exit ;
# No to exclusion checks, pushing commits upstream and telemetry submission
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
    # cp "$HOME"/.mozbuild/clang/lib/clang/"$(ls "$HOME"/.mozbuild/clang/lib/clang/)"/lib/windows/clang_rt.asan_dynamic-x86_64.pdb \
    #   /c/Program\ Files\ \(x86\)/Microsoft\ Visual\ Studio/2019/Enterprise/VC/Tools/MSVC/14.29.30133/bin/HostX64/x64/
    # MSVC 2022:
    cp "$HOME"/.mozbuild/clang/lib/clang/"$(ls "$HOME"/.mozbuild/clang/lib/clang/)"/lib/windows/clang_rt.asan_dynamic-x86_64.pdb \
        /c/Program\ Files/Microsoft\ Visual\ Studio/2022/Enterprise/VC/Tools/MSVC/14.34.31933/bin/HostX64/x64/
fi ;

echo "=== pytest attempt: 1 ===" ;
if ! BUILDSM="$*" python -u -m pytest --cov --mypy --pylint --ruff --ruff-format --ty --vulture ; then
    echo "=== pytest attempt: 2 ===" ;
    echo "=== Removing shell-cache ... ===" ;
    rm -rf "$HOME"/shell-cache/ ;
    echo "=== Removed shell-cache successfully! ===" ;
    if ! BUILDSM="$*" python -u -m pytest --cov --mypy --pylint --ruff --ruff-format --ty --vulture ; then
        echo "=== pytest attempt: 3 ===" ;
        echo "=== Removing shell-cache ... ===" ;
        rm -rf "$HOME"/shell-cache/ ;
        echo "=== Removed shell-cache successfully! ===" ;
        if ! BUILDSM="$*" python -u -m pytest --cov --mypy --pylint --ruff --ruff-format --ty --vulture ;
        then
            date > "$HOME"/pytest-failure.txt ;
        fi ;
    fi ;
fi ;
unset BUILDSM
popd || exit ;

# Remove m-c to free up more space for tarball creation
rm -rf "$HOME"/trees/firefox/ ;

# Create a tarball and SHA-256 checksum only if pytest ran without any errors
if [ ! -f "$HOME"/pytest-failure.txt ]; then
    pushd "$HOME"/shell-cache || exit ;
    for f in * ; do
        [[ $f =~ "js-" ]] && time tar -cpf - "$f" | zstd -T0 --long -19 > "$f".tar.zst ;
        shasum -a 256 -b "$f".tar.zst | tee "$f".tar.zst.sha256 ;
    done ;
    popd || exit ;
fi
