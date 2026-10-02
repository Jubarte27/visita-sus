#! /bin/bash
SCRIPT_DIR=$(dirname "$(realpath -e "${BASH_SOURCE[0]}")")

download_if_missing() {
    FILE_NAME=$1
    URL=$2
    FILE_PATH=$SCRIPT_DIR/data/$FILE_NAME

    if [ -f "$FILE_PATH" ]; then
        echo "$FILE_NAME" already exists, skiping
    else
        curl -L -o "$FILE_PATH" "$URL"
    fi
}

download_if_missing RS_setores_CD2022.gpkg https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF/RS/RS_setores_CD2022.gpkg
download_if_missing sul-260930.osm.pbf http://download.geofabrik.de/south-america/brazil/sul-260930.osm.pbf