import os
import csv
import json
import zipfile
import re
from io import BytesIO, StringIO
import polars as pl
import chardet
from xml.etree.ElementTree import parse as parse_xml

def extract_zip(file):
    """
    Extrai os arquivos de um ZIP e retorna uma lista com os caminhos dos arquivos extraídos.
    """
    try:
        print("Tentando processar um arquivo ZIP...")
        with zipfile.ZipFile(BytesIO(file.read()), 'r') as zip_ref:
            zip_ref.extractall('extracted_files')
            print("Arquivos extraídos com sucesso.")
        return [os.path.join('extracted_files', extracted_file) for extracted_file in os.listdir('extracted_files')]
    except Exception as e:
        raise RuntimeError(f"Erro ao descompactar arquivo ZIP: {str(e)}")

def process_zip(file):
    """
    Processa arquivos ZIP, delegando o processamento de cada tipo de arquivo a funções específicas.
    """
    try:
        # Extrai os arquivos do ZIP
        extracted_files = extract_zip(file)
        data = []

        # Processa cada arquivo extraído
        for file_path in extracted_files:
            file_name = os.path.basename(file_path)
            print(f"Processando arquivo: {file_name}")

            try:
                if file_name.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data.extend(process_json(f))

                elif file_name.endswith('.xml'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data.extend(process_xml(f))

                elif file_name.endswith('.csv'):
                    with open(file_path, 'rb') as f:
                        data.extend(process_csv(f))

                elif file_name.endswith('.xlsx'):
                    data.extend(process_excel(file_path))
                    
                elif file_name.endswith('.txt'):
                    with open(file_path, 'rb') as f:
                        data.extend(process_txt(f))    

                else:
                    print(f"Formato de arquivo desconhecido: {file_name}")
            except Exception as e:
                print(f"Erro ao processar o arquivo {file_name}: {e}")

        # Limpa a pasta temporária
        for file_path in extracted_files:
            os.remove(file_path)
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

    df = pl.read_csv(StringIO(content), separator=sep)
    return df.fill_null("N/A").to_dicts()

def load_dataframe(data):
    """Converte a lista de dicionários para um DataFrame Polars"""
    return pl.DataFrame(data)

def process_txt(file):
    """
    Processa um arquivo .txt, filtrando apenas as linhas que começam com '|'
    e descartando todo o conteúdo após o início de blocos inválidos.
    """
    try:
        # Lê o conteúdo do arquivo ignorando caracteres inválidos
        raw_data = file.read().decode('utf-8', errors='replace')
        
        # Lista para armazenar linhas válidas
        filtered_lines = []

        # Itera pelas linhas, adicionando somente as válidas
        for line in raw_data.splitlines():
            if line.strip().startswith('|'):
                filtered_lines.append(line)
            elif not line.strip():
                continue  # Ignora linhas em branco
            else:
                # Condição para parar ao encontrar um bloco inválido
                if not re.match(r'^[\w| ]+$', line.strip()):
                    print(f"Descartando bloco inválido: {line[:30]}...")
                    break

        # Verifica se há linhas válidas
        if not filtered_lines:
            raise ValueError("Nenhuma linha válida encontrada no arquivo.")

        # Junta as linhas válidas para processar como uma tabela
        content = "\n".join(filtered_lines)
        print("Linhas filtradas:")
        print(content[:5000])  # Depuração: mostra as linhas válidas antes do processamento

        # Lê as linhas usando Polars
        df = pl.read_csv(
            StringIO(content),  # Passa como StringIO para simular um arquivo
            separator='|',
            infer_schema_length=5000000,
            has_header=False,
            ignore_errors=True,
            truncate_ragged_lines=True
        )

        # Preenche valores nulos e retorna como lista de dicionários
        return df.fill_null("N/A").to_dicts()

    except Exception as e:
        print(f"Erro ao processar o arquivo .txt: {str(e)}")  # Detalhamento do erro
        raise RuntimeError(f"Erro ao processar o arquivo .txt: {str(e)}")
