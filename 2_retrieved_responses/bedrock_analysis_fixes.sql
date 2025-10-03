select count(*) as countresponses from responses
group by model_name,prompt_id
having countresponses>1 or countresponses=0
order by model_name,prompt_id asc;

select prompt_id,count(*),min(execution_datestamp),max(execution_datestamp) from responses where model_name='us.meta.llama4-maverick-17b-instruct-v1:0'
group by prompt_id;

select model_name,count(*) from responses
group by model_name;

-- There were two anomolous records with model name 'meta.llama4-scout-17b-instruct-v1:0'.
-- I removed these, since there are the expected number of records with model_name 'us.meta.llama4-scout-17b-instruct-v1:0'
begin;
delete from responses where model_name = 'meta.llama4-scout-17b-instruct-v1:0'
select changes()
commit;