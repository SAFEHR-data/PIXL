/*
 Given an accession number (i.e. the link between x-ray reports and DICOM
 studies, defined as a string) find the associated MRN (i.e. the internal
 patient identifier)
 */
set search_path to ${{ schema_name }},public;

select
    ls.mrn_id
from lab_sample as ls
where
	ls.external_lab_number = :accession

-- external_lab_number should really be unique, but limit 1 just in case
limit 1
