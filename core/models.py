from django.conf import settings
from django.db import models


class AuditLog(models.Model):
	action = models.CharField(max_length=100)
	model = models.CharField(max_length=120, blank=True, default='')
	object_id = models.CharField(max_length=120, blank=True, default='')
	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		related_name='audit_logs',
		null=True,
		blank=True,
	)
	data = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.action} - {self.model}#{self.object_id}"
