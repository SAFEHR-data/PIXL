/*
 Given an MRN (patient identifier), grab the associated date of birth, sex
 and ethnicity
 */
set search_path to ${{ schema_name }},public;

select
  cd.date_of_birth,
  cd.sex,
  cd.ethnicity

from core_demographic as cd
join mrn using(mrn_id)
where mrn.mrn = :mrn

order by greatest(cd.valid_from - :window_midpoint,
  :window_midpoint - cd.valid_from) -- abs(time difference)
limit 1
