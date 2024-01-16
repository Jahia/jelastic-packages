import org.jahia.services.content.JCRNodeWrapper
import org.jahia.services.content.decorator.JCRGroupNode
import org.jahia.services.content.decorator.JCRUserNode
import org.jahia.services.usermanager.JahiaGroupManagerService

def logFile = new File("/tmp/jahia_custom_metrics/jahia_privileged_users_count")

// wipe the file in case it already exist
logFile.text = ""

static def collectMembers(JCRGroupNode groupNode, Set<String> members) {
    for (JCRNodeWrapper member: groupNode.getMembers()) {
        if (member instanceof JCRUserNode) {
            members.add(member.getPath())
        } else if (member instanceof JCRGroupNode) {
            collectMembers(member, members)
        }
    }
    return members
}

Set<String> members = collectMembers(JahiaGroupManagerService.getInstance().lookupGroupByPath("/groups/privileged"), new HashSet<>())

logFile.append(members.size())
logFile.setWritable(true, false);
