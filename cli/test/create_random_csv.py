import random
import string

if __name__ == '__main__':

    f = open("random.csv", "a")
    f.write("VAL_ID,ACCESSION_NUMBER,STUDY_INSTANCE_UID,STUDY_DATE")
    for _ in range(100):
        s = ""
        for _ in range(3):
            s += ''.join(random.choices(string.ascii_letters, k=6))
            s += ','

        s += (f"{random.randint(0,1)}{random.randint(0,9)}"
              f"/{random.randint(0,2)}{random.randint(0,9)}"
              f"/2022 00:01:{random.randint(0, 5)}{random.randint(0,9)}")

        f.write(s + "\n")
