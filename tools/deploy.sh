#!/usr/bin/env bash

basedir=$(dirname "$0")
cd "${basedir}/.."
#echo -e "\033[33m${PWD}\033[0m"

setup=`cat setup.py | grep 'version='`

strings=(${setup//\'/ }) # 用 ' 进行split
version=${strings[1]}
echo "version: ${version}"

echo "Adding git tag ${version}"
git tag ${version}
# 如果在创建tag的时候发生了错误就立即返回
if [ $? -ne 0 ]; then exit $?; fi

remotes_raw=`git remote`
remotes=(${remotes_raw//\\n/ })
for remote in ${remotes[@]}
do
    echo "Pushing tag ${version} to ${remote}"
    git push ${remote} ${version}
done

echo "Uploading package to pypi"
python setup.py sdist upload -r pypi

echo "Deploy success"
