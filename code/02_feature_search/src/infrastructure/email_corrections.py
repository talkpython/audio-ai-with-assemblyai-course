replacement_endings = [
    ('@gmail', '@gmail.com'),
    ('@gmial.com', '@gmail.com'),
    ('@gmailcom', '@gmail.com'),
    ('@linuxmailorg', '@linuxmail.org'),
    ('@nerdyamigo', '@nerdyamigo.com'),
    ('@flytographer', '@flytographer.com'),
    ('@gmai.com', '@gmail.com'),
    ('@gmai', '@gmail.com'),
    ('@gmail.cm', '@gmail.com'),
    ('@gmail.co', '@gmail.com'),
    ('@mgial.com', '@gmail.com'),
    ('@gmail.cok', '@gmail.com'),
    ('@gmail.com.com', '@gmail.com'),
    ('@gmail.com2', '@gmail.com'),
    ('@gmail.coml', '@gmail.com'),
    ('@gmail.comm', '@gmail.com'),
    ('@gmail.comn', '@gmail.com'),
    ('@gmail.con', '@gmail.com'),
    ('@gmail.cpm', '@gmail.com'),
    ('@gmail.kcom', '@gmail.com'),
    ('@gmail.oom', '@gmail.com'),
    ('@gmail.vom', '@gmail.com'),
    ('@gmailc.om', '@gmail.com'),
    ('@gmaill.com', '@gmail.com'),
    ('@gmal.com', '@gmail.com'),
    ('@gmil.com', '@gmail.com'),
    ('@gmqil.com', '@gmail.com'),
    ('@gmsil.com', '@gmail.com'),
    ('@hotmai.com', '@hotmail.com'),
    ('@hotmai.com', '@hotmail.com'),
    ('@hotmail.comi', '@hotmail.com'),
    ('@hotmail.comia', '@hotmail.com'),
    ('@hotmail.copm', '@hotmail.com'),
    ('@hotmailcom', '@hotmail.com'),
    ('@oulook.com', '@outlook.com'),
    ('@oulook.fr', '@outlook.fr'),
    ('@outlokk.com', '@outlook.com'),
    ('@outloook.com', '@outlook.com'),
    ('@yahaoo.com', '@yahoo.com'),
    ('@yahoo.coms', '@yahoo.com'),
]


def fix_common_errors(email: str) -> str:
    if not email:
        return email

    email = email.strip().lower()

    for bad, good in replacement_endings:
        if email.endswith(bad):
            email = email.replace(bad, good)

    return email
