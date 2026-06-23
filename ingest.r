install.packages("read.dbc")

# COMMAND ----------

require("read.dbc")

origin_folder = "/dbc/"
destiny_folder = "/raw/csv/"

if (!dir.exists(destiny_folder)) {
  dir.create(destiny_folder)
}

files_names = list.files(origin_folder)

for (f in files_names){
  origin_path = paste(origin_folder, f, sep="")
  destiny_path = paste(destiny_folder, f, sep="")
  destiny_path = sub(".dbc", ".csv", destiny_path)
  df = read.dbc(origin_path)
  write.csv2(df, destiny_path, sep=";", row.names=FALSE)
}