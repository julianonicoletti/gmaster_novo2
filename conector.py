import os
import csv
import json
import zipfile
from io import BytesIO, StringIO
import polars as pl
import chardet
from xml.etree.ElementTree import parse as parse_xml

def process_zip(file):
    try:
        print("Tentando processar um arquivo ZIP...")
        with zipfile.ZipFile(BytesIO(file.read()), 'r') as zip_ref:
            zip_ref.extractall('extracted_files')
            print("Arquivos extraídos com sucesso.")

        extracted_files = os.listdir('extracted_files')
        data = []

        for extracted_file in extracted_files:
            file_path = os.path.join('extracted_files', extracted_file)
            if extracted_file.endswith('.xlsx'):
                df = pl.read_excel(file_path)
                data.extend(df.with_columns(pl.all().cast(str)).to_dicts())

            elif extracted_file.endswith('.json'):
                with open(file_path, 'r') as f:
                    file_data = json.load(f)
                    if isinstance(file_data, list) and all(isinstance(item, dict) for item in file_data):
                        data.extend(file_data)
                    else:
                        raise ValueError(f"Formato de JSON inválido no arquivo {extracted_file}. Esperado uma lista de objetos.")

            elif extracted_file.endswith('.xml'):
                tree = parse_xml(file_path)
                root = tree.getroot()
                xml_data = [{child.tag: child.text for child in elem} for elem in root]
                data.extend(xml_data)

            elif extracted_file.endswith('.csv'):
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']
                    content = raw_data.decode(encoding, errors='replace')
                    try:
                        sample = content.splitlines()[0:10]  # Pega as primeiras linhas como amostra
                        sniffer = csv.Sniffer()
                        dialect = sniffer.sniff("\n".join(sample))
                        sep = dialect.delimiter
                        print(f"Separador detectado: {sep}")
                    except Exception as e:
                        print(f"Erro ao detectar o separador: {e}")
                        sep = ','  # Fallback para vírgula como separador padrão
                        
                    df = pl.read_csv(StringIO(content), separator=sep, null_values=["", "null", "N/A"])
                
                    data = df.fill_null("N/A").to_dicts()
            
            elif extracted_file.endswith('.xlsx'):
                df = pl.read_excel(file_path)
                data.extend(df.with_columns(pl.all().cast(str)).to_dicts())

            else:
                print(f"Formato de arquivo desconhecido: {extracted_file}")

        for extracted_file in extracted_files:
            os.remove(os.path.join('extracted_files', extracted_file))
        os.rmdir('extracted_files')

        return data
    except Exception as e:
        raise RuntimeError(f"Erro ao processar arquivo ZIP: {str(e)}")

def process_excel(file):
    df = pl.read_excel(BytesIO(file.read()))
    return df.with_columns(pl.all().cast(str)).to_dicts()

def process_json(file):
    data = json.load(file)
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    else:
        raise ValueError("Formato de JSON inválido. Esperado uma lista de objetos.")

def process_xml(file):
    tree = parse_xml(BytesIO(file.read()))
    root = tree.getroot()
    xml_data = [{child.tag: child.text for child in elem} for elem in root]
    return xml_data

def process_csv(file):
    raw_data = file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    print(f"Codificação detectada: {encoding}")

    content = raw_data.decode(encoding, errors='replace')

    # Detecta o separador usando a biblioteca csv
    try:
        sample = content.splitlines()[0:10]  # Pega as primeiras linhas como amostra
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff("\n".join(sample))
        sep = dialect.delimiter
        print(f"Separador detectado: {sep}")
    except Exception as e:
        print(f"Erro ao detectar o separador: {e}")
        sep = ','  # Fallback para vírgula como separador padrão

    # Lê o CSV com Polars
    df = pl.read_csv(StringIO(content), separator=sep, null_values=["", "null", "N/A"])

    # Retorna os dados como lista de dicionários
    return df.fill_null("N/A").to_dicts()
