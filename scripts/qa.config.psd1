@{
    # This is an explicit local QA snapshot selection, not a discovery heuristic.
    # If this directory is removed or replaced, qa.ps1 fails closed until this
    # value is reviewed.  It is always resolved relative to the repository root.
    QAClusterDataRelativePath = ".qa-golden-pg-20260822\\data"

    Database = "datosenorden_pytest_goldenqa"
    DatabaseHost = "127.0.0.1"
    DatabasePort = 55432
    RuntimeRole = "deo_qa_runtime"

    FrontendPort = 3003
    BackendPort = 8004
}
