from sqlalchemy import BIGINT
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase, repr=True):  # type: ignore
    type_annotation_map = {
        int: BIGINT
    }