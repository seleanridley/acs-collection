#2018 population estimates aggregate and upload R script
#Guy Hydrick
#09/08/2019

#----start-----

library(dplyr)
library(reshape2)
library(RPostgres)

#read in population estimates file
file = "K:\\DataServices\\Datasets\\U.S. Census and Demographics\\Population_Estimates\\Raw\\2018\\sub-est2018_25.csv"
f = read.csv(file, header = TRUE, stringsAsFactors = FALSE)

#only take municipalities (sumlev==61) and the municipal name and estimates columns (from col 9 on) 
f = f[f$SUMLEV ==61,9:ncol(f)]

#drop the state column
f = f[,-2]

#rename columns to match existing data (previous years)
names(f) = c("NAME",
             "2010 Census",
             "2010 Estimate Base",
             "2010 Estimate",
             "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018")

#clean up name field - there is ' town' or ' city' after every record; some also have ' Town' before that again
f$NAME = gsub(' Town', '', substr(f$NAME, 1, nchar(f$NAME)-5))

#shorten Manchester-by-the-Sea to Manchester, so that it joins with key
f$NAME = gsub('-by-the-Sea','', f$NAME)

#from wide to long data
f = melt(f, measure.vars = colnames(f[,2:ncol(f)]))

#reorder by year, then alphabetically by municipal name
f = f[order(f[,2], f[,1]),]


#-----aggregations-----
#this whole section could be greatly improved; I was short on time -GPH

key = "K:\\DataServices\\Datasets\\Data Keys\\RegionalSummary\\muni_405_summary.csv"
k = read.csv(key, header=TRUE, stringsAsFactors = FALSE)

#full outer join of the munis (f) and the key (k)
big_T = merge(f,k, by.y="municipal", by.x = "NAME", all=TRUE)

#MAPC (id==352) is both in rpa_ia and region, though there are 3 munis more in the region
#we just want to keep the region, otherwise we will have two 352s in the end and we need a one-to-one for the join
#this effectively removes the rpa one from the final join
###there has to be a better way to do this
big_T[big_T$rpa_id==352, "rpa_id"] = 0

#similar with rural towns, both a community type and subtype
big_T[big_T$type_id==381, "type_id"] = 0

#correct Framingham value of 'A' - needs to be integer
#fortunately, this was for the 2010 census, which could be easily looked up and entered
big_T$value[big_T$NAME == "Framingham" & big_T$variable == "2010 Census"] = 68318

#cast value as integer
big_T$value = as.integer(big_T$value)

#read muni 405 full list
m405 = "K:\\DataServices\\Datasets\\Data Keys\\RegionalSummary\\Municipal_Summary_Key.csv"
m405 = read.csv(m405, header=TRUE, stringsAsFactors = FALSE)

#only keep the first 2 columns
m405 = m405[,1:2]

#column names
columns = c("muni_id", "years", "value")

#summarise by the different group types
###there has to be a better way to do this; I was trying lapply but couldn't get it to work
rpas = big_T %>% group_by(rpa_id, variable) %>% summarize(sum(value))
colnames(rpas)=columns

counties = big_T %>% group_by(county_id, variable) %>% summarize(sum(value))
colnames(counties)=columns

regions = big_T %>% group_by(region_id, variable) %>% summarize(sum(value))
colnames(regions)=columns

subregions = big_T %>% group_by(subreg_id, variable) %>% summarize(sum(value))
colnames(subregions)=columns

types = big_T %>% group_by(type_id, variable) %>% summarize(sum(value))
colnames(types)=columns

sub_types = big_T %>% group_by(subtype_id, variable) %>% summarize(sum(value))
colnames(sub_types)=columns

#metrofuture
mf = big_T %>% group_by(mf, variable) %>% summarize(sum(value))
mf[mf==1] = 354   #mf (metrofuture) is a binary column; have to give it the proper muni id
colnames(mf)=columns

#total
total = big_T %>% group_by(variable) %>% summarize(sum(value))
total$muni_id = 353
colnames(total) = c("years", "value", "muni_id")	#different order from others

#combine all aggregations
extra_aggs = bind_rows(
  list(
    as.data.frame(rpas),
    as.data.frame(counties),
    as.data.frame(regions),
    as.data.frame(subregions),
    as.data.frame(types),
    as.data.frame(sub_types),
    as.data.frame(mf),
    as.data.frame(total)
    )
  )

big_T = big_T[,2:4]

names(big_T)[names(big_T) == 'variable'] = 'years'

cur351 = merge(m405[1:351,], big_T, by.x='muni_id', by.y= 'muni_Id', all.x = TRUE)

#create df for the current year's data and muni 352-405 aggregations
cur405 = merge(m405[352:405,],extra_aggs, all.x = TRUE)

cur_all = bind_rows(list(cur351,cur405))
cur_all$years = as.character(cur_all$years)

colnames(cur_all)[4] = 'pop_est'

cur_all = cur_all[order(cur_all[,3], cur_all[,1]),]


#-----SQL part-----

#con <- dbConnect(RPostgres::Postgres(), host='10.10.10.240', '5432', dbname='ds', user='mapc', password='M@PC_933')  #sdvem
con <- dbConnect(RPostgres::Postgres(), host='db.live.mapc.org', '5433', dbname='ds', user='mapc', password='M@PC_933')  #db.live

#create backup of last years estimates
res = dbSendQuery(con, "SELECT * INTO tabular.demo_pop_estimates_2017_m FROM tabular.demo_pop_estimates_m;")
dbClearResult(res)

#truncate existing table
res = dbSendQuery(con, "TRUNCATE tabular.demo_pop_estimates_m;")
dbClearResult(res)

#need in order to specify schema in dbWriteTable
a = DBI::Id(schema='tabular', table='demo_pop_estimates_m')	

#append new pop estimates to existing table (already has correct name, etc.) for the data browser
dbWriteTable(con, a, cur_all, append=TRUE)

