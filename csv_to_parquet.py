import os
import sys
import pandas as pd

# Try pyarrow first, then fastparquet as a fallback
use_pyarrow = False
use_fastparquet = False
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    use_pyarrow = True
    print('Usando pyarrow para escrever Parquet')
except Exception as e:
    print(f'pyarrow indisponível: {e}')
    try:
        import fastparquet
        from fastparquet import write as fp_write
        use_fastparquet = True
        print('Usando fastparquet para escrever Parquet')
    except Exception as e2:
        print(f'fastparquet indisponível: {e2}')
        raise ImportError('Nenhum motor Parquet disponível. Instale pyarrow ou fastparquet no seu ambiente.')

def find_csv_files(folders):
    files = []
    for folder in folders:
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                if f.lower().endswith('.csv'):
                    files.append(os.path.join(folder, f))
    return sorted(files)

def collect_union_columns(csv_files, sep=';', encoding='latin1'):
    cols = []
    for path in csv_files:
        try:
            df0 = pd.read_csv(path, nrows=0, sep=sep, encoding=encoding)
            base = os.path.splitext(os.path.basename(path))[0]
            # add provenance cols if pattern matches
            if '_' in base and len(base.split('_')[1]) == 4:
                prov = ['estado_origem','ano_origem','mes_origem']
                for c in prov:
                    if c not in cols:
                        cols.append(c)
            for c in df0.columns:
                if c not in cols:
                    cols.append(c)
        except Exception as e:
            print(f"Aviso: não foi possível ler cabeçalho de {path}: {e}")
    return cols

def chunked_csv_to_parquet(csv_files, out_path, sep=';', encoding='latin1', chunksize=100000):
    if not csv_files:
        print("Nenhum CSV para processar.")
        return

    # ensure output root dir (out_path is a folder)
    out_root = out_path
    if out_root and not os.path.exists(out_root):
        os.makedirs(out_root, exist_ok=True)

    # processed log to avoid reprocessing
    # format: either 'base' (legacy, means done) or 'base|rows' where rows is number of rows already written
    processed_log = os.path.join(out_root, 'processed.log')
    processed = {}  # base -> rows_written (int) or -1 for done
    if os.path.exists(processed_log):
        try:
            with open(processed_log, 'r', encoding='utf-8') as fh:
                for line in fh:
                    s = line.strip()
                    if not s:
                        continue
                    if '|' in s:
                        base, rows = s.split('|', 1)
                        try:
                            processed[base] = int(rows)
                        except Exception:
                            processed[base] = 0
                    else:
                        # legacy entry: assume fully processed
                        processed[s] = -1
        except Exception:
            processed = {}

    def _write_processed_log(pmap):
        try:
            with open(processed_log + '.tmp', 'w', encoding='utf-8') as fh:
                for k, v in pmap.items():
                    if v == -1:
                        fh.write(f"{k}\n")
                    else:
                        fh.write(f"{k}|{v}\n")
            os.replace(processed_log + '.tmp', processed_log)
        except Exception as e:
            print(f"Aviso: não foi possível gravar processed.log: {e}")

    # collect union of columns (cheap: reads only headers)
    print("Coletando cabeçalhos para unificar colunas...")
    union_cols = collect_union_columns(csv_files, sep=sep, encoding=encoding)
    if not union_cols:
        print("Nenhuma coluna encontrada.")
        return

    # writers per file (for pyarrow) or compression tracking for fastparquet
    writers = {}  # base -> (ParquetWriter, compression)
    fastparquet_written = {}  # base -> compression
    total_rows = 0

    try:
        for path in csv_files:
            print(f"Processando arquivo: {path}")
            base = os.path.splitext(os.path.basename(path))[0]

            if base in processed:
                print(f"  Pulando {base} (já processado)")
                continue
            estado = ano = mes = None
            if '_' in base and len(base.split('_')[1]) == 4:
                estado, anomes = base.split('_')
                ano = anomes[:2]
                mes = anomes[2:]
            # read in chunks
            try:
                iterator = pd.read_csv(path, sep=sep, encoding=encoding, chunksize=chunksize, low_memory=False)
            except Exception as e:
                print(f"Erro ao abrir {path}: {e}")
                continue
            for chunk in iterator:
                # add provenance columns if applicable
                if estado is not None:
                    chunk['estado_origem'] = estado
                    # ano is two-digit string like '25' -> convert to full year 2025
                    try:
                        year_full = 2000 + int(ano)
                    except Exception:
                        year_full = None
                    chunk['ano_origem'] = year_full if year_full is not None else ano
                    chunk['mes_origem'] = mes

                # align columns to union_cols (add missing with NA)
                for c in union_cols:
                    if c not in chunk.columns:
                        chunk[c] = pd.NA
                # reorder
                chunk = chunk[union_cols]

                # output file per CSV
                out_file = os.path.join(out_root, f"{base}.parquet")

                # support resuming partially processed files: skip rows already written
                already = processed.get(base, 0)
                if already == -1:
                    print(f"  Pulando {base} (já processado)")
                    break
                # skip whole chunks until reaching 'already'
                if already > 0:
                    # maintain skipped count across chunks
                    if 'skipped_count' not in locals():
                        skipped_count = 0
                    if skipped_count < already:
                        if skipped_count + len(chunk) <= already:
                            skipped_count += len(chunk)
                            # skip this entire chunk
                            continue
                        else:
                            # need to chop the chunk
                            skip_in_chunk = already - skipped_count
                            chunk = chunk.iloc[skip_in_chunk:]
                            skipped_count = already

                # Try to use stronger compression (zstd > gzip > snappy)
                preferred_compressions = ['zstd', 'gzip', 'snappy']
                if use_pyarrow:
                    table = pa.Table.from_pandas(chunk, preserve_index=False)
                    if base not in writers:
                        # find a supported compression for this environment
                        created = False
                        for comp in preferred_compressions:
                            try:
                                w = pq.ParquetWriter(out_file, table.schema, compression=comp)
                                writers[base] = (w, comp)
                                created = True
                                break
                            except Exception:
                                continue
                        if not created:
                            # fallback to no compression
                            w = pq.ParquetWriter(out_file, table.schema)
                            writers[base] = (w, None)
                    writer, used_comp = writers[base]
                    try:
                        writer.write_table(table)
                    except Exception:
                        try:
                            tbl2 = pa.Table.from_pandas(chunk, schema=writer.schema, preserve_index=False)
                            writer.write_table(tbl2)
                        except Exception as e2:
                            print(f"Erro ao escrever chunk de {path} em {out_file}: {e2}")
                            raise
                    total_rows += table.num_rows
                    # update processed counts and persist
                    processed[base] = processed.get(base, 0) + table.num_rows
                    _write_processed_log(processed)
                    print(f"  escrito chunk ({table.num_rows} linhas) em {out_file} (compress={used_comp}). Total até agora: {total_rows}")
                elif use_fastparquet:
                    try:
                        # sanitize chunk for fastparquet: ensure consistent types and replace pd.NA with None
                        import pandas.api.types as ptypes
                        for col in chunk.columns:
                            # fill missing with None
                            if chunk[col].isna().any():
                                chunk[col] = chunk[col].where(pd.notna(chunk[col]), None)
                            # for object/string columns, convert str->bytes (fastparquet low-level expects bytes)
                            if ptypes.is_object_dtype(chunk[col]) or ptypes.is_string_dtype(chunk[col]):
                                def _to_bytes(x):
                                    if x is None:
                                        return None
                                    if isinstance(x, (bytes, bytearray)):
                                        return bytes(x)
                                    return str(x).encode('utf-8')
                                chunk[col] = chunk[col].map(_to_bytes)
                        
                        
                        
                        
                        
                    except Exception:
                        pass
                    try:
                        if base not in fastparquet_written:
                            # try preferred compressions until one works
                            chosen = None
                            for comp in preferred_compressions:
                                try:
                                    fp_write(out_file, chunk, file_scheme='simple', write_index=False, compression=comp)
                                    chosen = comp
                                    break
                                except Exception:
                                    continue
                            if chosen is None:
                                # try without specifying compression
                                fp_write(out_file, chunk, file_scheme='simple', write_index=False)
                                chosen = None
                            fastparquet_written[base] = chosen
                        else:
                            comp = fastparquet_written[base]
                            if comp is None:
                                fp_write(out_file, chunk, file_scheme='simple', write_index=False, append=True)
                            else:
                                fp_write(out_file, chunk, file_scheme='simple', write_index=False, append=True, compression=comp)
                        total_rows += len(chunk)
                        # update processed counts and persist
                        processed[base] = processed.get(base, 0) + len(chunk)
                        _write_processed_log(processed)
                        print(f"  escrito chunk ({len(chunk)} linhas) em {out_file}. Total até agora: {total_rows}")
                    except Exception as e:
                        print(f"Erro ao escrever chunk com fastparquet de {path} em {out_file}: {e}")
                        raise
            # se chegou aqui sem exceção no processamento deste arquivo, marca como processado
            try:
                processed[base] = -1
                _write_processed_log(processed)
                print(f"  Marcado como processado: {base}")
                # clear skipped_count for next file
                if 'skipped_count' in locals():
                    del skipped_count
            except Exception as e:
                print(f"Aviso: não foi possível atualizar processed.log: {e}")
        print(f"Feito. Total de linhas escritas: {total_rows}")
    finally:
        if use_pyarrow and writers:
            for tup in writers.values():
                try:
                    writer_obj = tup[0] if isinstance(tup, tuple) else tup
                    writer_obj.close()
                except Exception:
                    pass

def main():
    candidate_folders = [os.path.join('raw', 'csv')]
    csv_files = find_csv_files(candidate_folders)

    if not csv_files:
        print('Nenhum arquivo CSV encontrado nas pastas: ' + ','.join(candidate_folders))
        sys.exit(0)

    # always write to raw/parquet
    out_folder = os.path.join('raw', 'parquet')
    if not os.path.isdir(out_folder):
        os.makedirs(out_folder, exist_ok=True)
    # out_path used as output root folder
    out_path = out_folder

    print(f"Arquivos encontrados: {len(csv_files)}")
    chunked_csv_to_parquet(csv_files, out_path, sep=';', encoding='latin1', chunksize=100000)

if __name__ == '__main__':
    main()
# %%
