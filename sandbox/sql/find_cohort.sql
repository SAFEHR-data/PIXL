/*
 Find all the instances of the lab order that concerns the placement of the
 nasogastric tube. The 'internal_id' links to the DICOM study instance.
 Comment in fields for more information on the resulting rows.
*/
set search_path to ${{ schema_name }},public;

select
    --lb.battery_code,
	--lb.battery_name,
	--lb.description,
	--ltd.test_lab_code,
	--lr.value_as_text,
    --lo.hospital_visit_id,
    --greatest(ls.sample_collection_datetime,
    --lr.result_last_modified_datetime,
    --lo.order_datetime,
    --lo.request_datetime,
    --ls.receipt_at_lab_datetime) as lab_time,
    ls.external_lab_number,
    mrn.mrn
from lab_battery as lb
join lab_order as lo using(lab_battery_id)
join lab_result as lr using(lab_order_id)
join lab_test_definition as ltd using(lab_test_definition_id)
join lab_sample as ls using(lab_sample_id)
join mrn using(mrn_id)
where
	lb.lab_provider = 'PACS'
	and lb.battery_name = 'XR Chest Nasogastric Tube Position'
    and ltd.test_lab_code = 'TEXT'
    and lo.request_datetime > '2022-04-01'
    and lo.request_datetime < '2022-08-01'
    and mrn.research_opt_out is false
