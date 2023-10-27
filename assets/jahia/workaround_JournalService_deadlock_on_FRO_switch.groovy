def jackrabbit = org.jahia.services.SpringContextSingleton.getBean("jackrabbit");
def journal = jackrabbit.getClusterNode().journal;
def repository = jackrabbit.getRepository()
def ivmf = org.jahia.services.content.impl.jackrabbit.JahiaAbstractJournal.class.getDeclaredField("internalVersionManager");
ivmf.setAccessible(true);
def ivm = ivmf.get(journal)
log.info("Current value: "+ ivm);
if (ivm == null) {
  def ctxf = org.apache.jackrabbit.core.RepositoryImpl.class.getDeclaredField("context");
  ctxf.setAccessible(true);
  ivm = ctxf.get(repository).getInternalVersionManager();
  log.info("Resetting to: "+ ivm );
  ivmf.set(journal, ivm);
}
