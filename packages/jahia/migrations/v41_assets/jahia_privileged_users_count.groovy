import org.jahia.services.content.JCRNodeWrapper
import org.jahia.services.content.JCRSessionWrapper
import org.jahia.services.content.JCRTemplate
import org.jahia.services.content.decorator.JCRGroupNode
import org.jahia.services.content.decorator.JCRUserNode
import org.jahia.services.usermanager.JahiaGroupManagerService

static def collectMembers(JCRGroupNode groupNode, Set<String> members, Set<String> checkedGroups, JCRSessionWrapper session,def log, def startTime) {
    if (checkedGroups.contains(groupNode.getPath())) {
        return members
    }

    System.out.println("check for group: " + groupNode.getPath())
    checkedGroups.add(groupNode.getPath())
    for (JCRNodeWrapper member : groupNode.getMembers()) {
        if (member instanceof JCRUserNode) {
            members.add(member.getPath())
    if (members.size() % 10000 == 0) {
       log.info("{}s 10k members found ({}) - reset session cache.", (System.currentTimeMillis() - startTime) / 1000.0, members.size())
       session.refresh(false);
    }
        } else if (member instanceof JCRGroupNode) {
            collectMembers(member, members, checkedGroups, session, log, startTime)
        }
    }
    // refresh the session to prevent too much nodes being stored in cache. 
    return members
}

long startTime = System.currentTimeMillis();
JCRTemplate.getInstance().doExecuteWithSystemSession {session ->
    Set<String> members = collectMembers(JahiaGroupManagerService.getInstance().lookupGroupByPath("/groups/privileged", session), new HashSet<>(), new HashSet<>(), session, log, startTime)
    // log.info("members : ")
    for (String member : members) {
       // log.info(" - {}", member)
    }
log.info("{}s - members : {}", (System.currentTimeMillis() - startTime) / 1000.0, members.size())
}
